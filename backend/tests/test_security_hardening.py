"""安全加固与反凑数校验测试。

覆盖：
1. 登录 token 过期机制（7 天有效）
2. 邀请码防爆破（5 次失败后锁定 15 分钟）
3. SQL 空壳表反凑数
4. MD 重复字符反凑数
5. Code 空函数体反凑数
6. 知识库无匹配时回退到通用项目
"""
from datetime import datetime, timedelta
import pytest
from app.services import auth_service, member_service, validate_service, knowledge_service
from app import models


# ============ token 过期 ============
def test_token_has_expires_at():
    """注册后 token 应携带过期时间。"""
    r = auth_service.register("u_expire", "pw", "测试")
    user = models.get_user_by_token(r["token"])
    assert user["token_expires_at"] is not None


def test_expired_token_rejected():
    """过期 token 应被拒绝并清除。"""
    r = auth_service.register("u_expired", "pw", "测试")
    # 手动将过期时间设为过去
    with models.db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET token_expires_at=? WHERE username=?",
            ((datetime.now() - timedelta(days=1)).isoformat(), "u_expired"))
    user = auth_service.get_user_by_token(r["token"])
    assert user is None
    # token 应被清除
    again = models.get_user_by_token(r["token"])
    assert again is None


def test_fresh_token_accepted():
    """新 token 应可正常使用。"""
    r = auth_service.register("u_fresh", "pw", "测试")
    user = auth_service.get_user_by_token(r["token"])
    assert user is not None
    assert user["username"] == "u_fresh"


# ============ 邀请码防爆破 ============
def _setup_leader_and_project(username="leader"):
    r = auth_service.register(username, "pw", "队长")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.set_project_creator(pid, r["user"]["id"])
    models.add_project_member(pid, r["user"]["id"], "leader")
    return pid, r["user"]["id"], r["token"]


def test_invite_locked_after_5_failures():
    """同一邀请码连续 5 次失败后应被锁定 15 分钟。"""
    pid, _, leader_token = _setup_leader_and_project("lock_leader")
    inv = member_service.generate_invite(pid, leader_token)
    invite = models.get_invite_by_code(inv["code"])
    # 模拟 5 次失败
    for _ in range(5):
        models.increment_invite_fail(invite["id"])
    # 第 6 次应被锁定
    invite_after = models.get_invite_by_code(inv["code"])
    assert invite_after["fail_count"] >= 5
    assert invite_after["locked_until"] is not None
    # 锁定后尝试加入应抛错
    member = auth_service.register("m_lock", "pw", "队员")
    with pytest.raises(ValueError, match="锁定"):
        member_service.join_with_code(inv["code"], member["token"])


def test_invite_fail_reset_on_success():
    """成功加入后失败计数应清零。"""
    pid, _, leader_token = _setup_leader_and_project("reset_leader")
    inv = member_service.generate_invite(pid, leader_token)
    invite = models.get_invite_by_code(inv["code"])
    # 先累计 3 次失败
    for _ in range(3):
        models.increment_invite_fail(invite["id"])
    member = auth_service.register("m_reset", "pw", "队员")
    member_service.join_with_code(inv["code"], member["token"])
    # 成功后 fail_count 应清零
    invite_after = models.get_invite_by_code(inv["code"])
    assert invite_after["fail_count"] == 0
    assert invite_after["locked_until"] is None


# ============ SQL 反凑数 ============
def test_sql_empty_table_rejected():
    """每张表必须有列定义，空壳表应失败。"""
    # 第一张表括号里只有 1 列，疑似空壳
    shell_sql = """
    CREATE TABLE users (id INTEGER PRIMARY KEY);
    CREATE TABLE orders (id INTEGER PRIMARY KEY, FOREIGN KEY (uid) REFERENCES users(id));
    """
    r = validate_service.validate_sql(shell_sql)
    assert r["pass"] is False
    assert any("空壳" in x for x in r["reasons"])


def test_sql_with_real_columns_passes():
    """每张表有 ≥2 列定义应通过。"""
    real_sql = """
    CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
    CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id));
    """
    r = validate_service.validate_sql(real_sql)
    assert r["pass"] is True


# ============ MD 反凑数 ============
def test_md_repeated_content_rejected():
    """重复字符凑字数应失败。"""
    # 500+ 字符但全为重复
    repeat_md = "## 需求\n" + "用户功能" * 200
    r = validate_service.validate_md(repeat_md)
    assert r["pass"] is False
    assert any("去重率" in x for x in r["reasons"])


def test_md_normal_content_passes():
    """正常多段内容应通过。"""
    normal_md = """## 需求

本项目目标用户为高校学生，需要管理课程设计任务。系统需要支持任务拆解、进度追踪和提醒功能，让用户可创建项目并上传产物。

## 功能

- 任务自动拆解：基于 SDLC 混合模型生成里程碑与子任务
- 里程碑校验：上传 sql/md/code 等产物自动结构校验
- 飞书通知推送：定时扫描逾期任务并主动推送到飞书群
- 动态重规划：检测产能缺口，LLM 提案砍需求保核心任务
- 团队协作：邀请码加入项目、队长分配任务、队员认领提交

## 用户

学生队长与队员，角色严格分工。队长负责创建项目、生成邀请码、分配任务、审阅队员提交的产物。队员加入项目后认领任务、上传交付物并接受队长审阅。系统会在任务逾期时主动推送通知到飞书群，避免错过 deadline。

指导教师可作为观察者查看团队真实进度，无需参与具体操作。整个流程通过确定性状态机约束，避免 LLM 失控影响项目状态。

## 技术架构

后端采用 FastAPI 异步框架，SQLite 单文件存储，部署简单。前端使用 Alpine.js 实现 SPA 无构建步骤。LLM 接入 DeepSeek 兼容 OpenAI 协议，可灵活替换。通知采用飞书自定义机器人 webhook 推送，定时调度使用 APScheduler 后台守护进程。状态机层强制约束任务和里程碑状态转移，非法转换抛 InvalidTransition 异常。
"""
    r = validate_service.validate_md(normal_md)
    assert r["pass"] is True, r["reasons"]


# ============ Code 反凑数 ============
def test_python_empty_function_body_rejected():
    """Python 函数体为 pass 或空应失败。"""
    shell_py = """
def add(a, b):
    pass

def sub(a, b):
    pass
"""
    r = validate_service.validate_code(shell_py, "py")
    assert r["pass"] is False
    assert any("空函数" in x for x in r["reasons"])


def test_python_real_function_body_passes():
    """有真实函数体应通过。"""
    real_py = """
def add(a, b):
    return a + b

def sub(a, b):
    return a - b
"""
    r = validate_service.validate_code(real_py, "py")
    assert r["pass"] is True


# ============ 知识库兜底 ============
def test_kb_fallback_to_flask_when_no_match():
    """无任何关键词匹配时，回退到 flask 通用项目。"""
    r = knowledge_service.match_references("做一个区块链智能合约系统")
    assert r["projects"] == ["flask"]


def test_kb_fallback_to_taro_for_miniprogram_keyword():
    """含小程序子串但不在 keywords 中时，应触发兜底。"""
    r = knowledge_service.match_references("做一个手机端 App")
    # "手机端" 不在 keywords，"App" 不在 keywords，回退 flask
    assert "flask" in r["projects"]
