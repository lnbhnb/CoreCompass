import pytest
from unittest.mock import patch
from app.services import project_service, validate_service
from app import models
from app.state_machine import MilestoneStatus

FALLBACK_PLAN = {
    "milestones": [
        {"name": "数据库", "expected_artifact_type": "sql", "tasks": [
            {"title": "建表", "priority": "core", "est_effort_days": 1.0, "week": 1}]},
        {"name": "实现", "expected_artifact_type": "code", "tasks": [
            {"title": "API", "priority": "core", "est_effort_days": 2.0, "week": 2}]}]}

VALID_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id));
"""
EMPTY_SQL = "-- nothing"


@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
@pytest.mark.asyncio
async def test_lock_then_unlock(mock_llm):
    pid = project_service.create_project_with_plan("p", "2026-08-20", 3, "topic")
    ms_id = models.list_milestones(pid)[0]["id"]
    r = await validate_service.validate_milestone_artifact(ms_id, "empty.sql", EMPTY_SQL.encode())
    assert r["pass"] is False
    assert models.get_milestone(ms_id)["status"] == MilestoneStatus.LOCKED.value
    r = await validate_service.validate_milestone_artifact(ms_id, "valid.sql", VALID_SQL.encode())
    assert r["pass"] is True
    assert models.get_milestone(ms_id)["status"] == MilestoneStatus.DONE.value
    assert validate_service.can_proceed_to_next(pid, ms_id) is True
