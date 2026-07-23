import pytest
from unittest.mock import patch, MagicMock
from app.services import project_service, validate_service, replan_service, notify_service
from app import models, config
from app.state_machine import MilestoneStatus

FALLBACK_PLAN = {
    "milestones": [
        {"name": "数据库设计", "expected_artifact_type": "sql", "tasks": [
            {"title": "建表", "priority": "core", "est_effort_days": 1.0, "week": 1}]},
        {"name": "核心实现", "expected_artifact_type": "code", "tasks": [
            {"title": "后端 API", "priority": "core", "est_effort_days": 2.0, "week": 2},
            {"title": "前端页面", "priority": "optional", "est_effort_days": 1.5, "week": 2}]}]}

VALID_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id));
"""


@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
@patch("app.services.notify_service.httpx.post")
@pytest.mark.asyncio
async def test_e2e_three_highlights(mock_post, mock_plan):
    """三段式 Demo 完整闭环"""
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"StatusCode": 0})
    monkeypatch_target = config
    monkeypatch_target.FEISHU_WEBHOOK_URL = "https://example.com/hook"
    monkeypatch_target.FEISHU_SECRET = ""

    # 段1：创建项目
    pid = project_service.create_project_with_plan("Demo", "2026-08-20", 3, "校园二手交易平台")
    assert len(models.list_tasks_by_project(pid)) == 3

    # 段2：突出点① 实体验证（先失败后通过）
    ms1 = models.list_milestones(pid)[0]
    r = await validate_service.validate_milestone_artifact(ms1["id"], "empty.sql", b"-- nothing")
    assert r["pass"] is False
    assert models.get_milestone(ms1["id"])["status"] == MilestoneStatus.LOCKED.value

    r = await validate_service.validate_milestone_artifact(ms1["id"], "valid.sql", VALID_SQL.encode())
    assert r["pass"] is True
    assert models.get_milestone(ms1["id"])["status"] == MilestoneStatus.DONE.value

    # 段3：突出点② 重规划（模拟偏航 + 应用提案）
    tasks = models.list_tasks_by_project(pid)
    models.update_task_status(tasks[0]["id"], "doing")
    models.update_task_status(tasks[0]["id"], "overdue")
    proposal = replan_service.propose_replan(pid, remaining_days=1, team_size=1)
    assert proposal["gap_days"] > 0
    result = replan_service.apply_replan(pid, proposal["proposal"], remaining_days=1, team_size=1)
    assert result["applied"] is True
    cut = [t for t in models.list_tasks_by_project(pid, include_cut=True) if t["status"] == "cut"]
    assert len(cut) >= 1
    assert all(t["priority"] == "optional" for t in cut)

    # 段4：突出点③ 飞书推送
    r = notify_service.send_feishu("测试", project_id=pid, msg_type="manual_test")
    assert r["status"] == "sent"
    assert len(models.list_notifications(pid)) >= 1
