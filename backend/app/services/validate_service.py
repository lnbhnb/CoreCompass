import re
import ast
import json
import yaml
import sqlparse
from typing import Dict, Any
from app import models
from app.llm import client
from app.state_machine import MilestoneStatus


def validate_sql(content: str) -> Dict[str, Any]:
    reasons = []
    sql_text = " ".join(str(p) for p in sqlparse.parse(content)).upper()
    if len(re.findall(r"CREATE\s+TABLE", sql_text)) < 2:
        reasons.append("表数量不足：< 2")
    if "PRIMARY KEY" not in sql_text:
        reasons.append("缺少 PRIMARY KEY")
    if "FOREIGN KEY" not in sql_text:
        reasons.append("缺少 FOREIGN KEY（外键）")
    # 反凑数：每张表必须有列定义（CREATE TABLE name (...) 括号内至少 2 列）
    table_blocks = re.findall(r"CREATE\s+TABLE\s+\w+\s*\(([^)]+)\)", content, re.IGNORECASE)
    for i, block in enumerate(table_blocks):
        # 列数估算：按逗号分割，剔除约束子句
        cols = [c.strip() for c in block.split(",") if c.strip()]
        if len(cols) < 2:
            reasons.append(f"第 {i+1} 张表列定义不足（疑似空壳表）")
    return {"pass": not reasons, "reasons": reasons}


def validate_md(content: str) -> Dict[str, Any]:
    reasons = []
    if len(content) < 500:
        reasons.append(f"字数不足：{len(content)} < 500")
    if len(re.findall(r"^##\s", content, re.MULTILINE)) < 3:
        reasons.append("H2 标题不足 < 3")
    missing = [k for k in ["需求", "功能", "用户"] if k not in content]
    if missing:
        reasons.append(f"缺少关键词：{missing}")
    # 反凑数：分词去重率检测，避免重复字符串凑字数
    tokens = re.findall(r"[\u4e00-\u9fa5]|[a-zA-Z]+", content)
    if tokens:
        unique_ratio = len(set(tokens)) / len(tokens)
        if unique_ratio < 0.4:
            reasons.append(f"字符去重率过低：{unique_ratio:.0%}（疑似重复凑字数）")
    return {"pass": not reasons, "reasons": reasons}


def validate_code(content: str, language: str) -> Dict[str, Any]:
    reasons = []
    try:
        if language == "py":
            tree = ast.parse(content)
            defs = [n for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
            # 反凑数：每个函数必须有非空 body
            empty_funcs = [n for n in ast.walk(tree)
                           if isinstance(n, ast.FunctionDef)
                           and (not n.body or all(isinstance(b, ast.Pass) for b in n.body))]
            if empty_funcs:
                reasons.append(f"存在 {len(empty_funcs)} 个空函数体（疑似空壳）")
        else:
            defs = re.findall(r"(function\s+\w+|class\s+\w+|=>\s*{)", content)
        if len(defs) < 2:
            reasons.append(f"函数/类定义不足：{len(defs)} < 2")
        if len(content.strip()) < 50:
            reasons.append("实现过于简单（疑似空壳）")
    except SyntaxError as e:
        reasons.append(f"语法错误：{e}")
    return {"pass": not reasons, "reasons": reasons}


def validate_json_schema(content: str) -> Dict[str, Any]:
    reasons = []
    try:
        data = json.loads(content) if content.strip().startswith("{") else yaml.safe_load(content)
        if not isinstance(data, dict):
            reasons.append("顶层不是对象")
            return {"pass": False, "reasons": reasons}
        missing = [f for f in ["name", "endpoints"] if f not in data]
        if missing:
            reasons.append(f"缺少必填字段：{missing}")
    except Exception as e:
        reasons.append(f"解析失败：{e}")
    return {"pass": not reasons, "reasons": reasons}


VALIDATORS = {
    "sql": validate_sql,
    "md": validate_md,
    "json": validate_json_schema,
    "yaml": validate_json_schema,
    "py": lambda c: validate_code(c, "py"),
    "js": lambda c: validate_code(c, "js"),
    "ts": lambda c: validate_code(c, "js"),
}


async def validate_milestone_artifact(milestone_id: int, filename: str, content: bytes):
    ms = models.get_milestone(milestone_id)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "other"
    text = content.decode("utf-8", errors="ignore")
    validator = VALIDATORS.get(ext)
    llm_used = False
    if validator:
        result = validator(text)
    else:
        result = client.validate_with_llm(ms["name"], ext, text)
        llm_used = True
    fail_reasons = json.dumps(result.get("reasons", []), ensure_ascii=False)
    models.insert_validation(
        milestone_id, filename, ext,
        "pass" if result.get("pass") else "fail",
        fail_reasons, llm_used)
    if result.get("pass"):
        models.update_milestone_status(milestone_id, MilestoneStatus.DONE.value)
    else:
        models.update_milestone_status(milestone_id, MilestoneStatus.LOCKED.value)
    return result


def can_proceed_to_next(project_id: int, current_milestone_id: int) -> bool:
    return models.get_milestone(current_milestone_id)["status"] == MilestoneStatus.DONE.value
