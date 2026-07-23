import pytest
from unittest.mock import patch
from app.services import project_service

FALLBACK_PLAN = {
    "milestones": [
        {"name": "需求", "expected_artifact_type": "md", "tasks": [
            {"title": "需求文档", "priority": "core", "est_effort_days": 1.0, "week": 1}]},
        {"name": "数据库", "expected_artifact_type": "sql", "tasks": [
            {"title": "表结构", "priority": "core", "est_effort_days": 1.0, "week": 2}]}]}


@patch("app.services.project_service.client.generate_initial_plan_with_kb", return_value=FALLBACK_PLAN)
def test_create_project_with_plan(mock_llm):
    result = project_service.create_project_with_plan(
        "二手平台", "2026-08-20", 3, "校园二手交易平台")
    pid = result["project_id"]
    detail = project_service.get_project_detail(pid)
    assert detail["project"]["name"] == "二手平台"
    assert len(detail["milestones"]) == 2
    assert len(detail["tasks"]) == 2
    assert detail["tasks"][0]["priority"] == "core"
    assert "used_references" in result
