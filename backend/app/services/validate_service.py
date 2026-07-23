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
    return {"pass": not reasons, "reasons": reasons}


def validate_code(content: str, language: str) -> Dict[str, Any]:
    reasons = []
    try:
        if language == "py":
            tree = ast.parse(content)
            defs = [n for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
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
