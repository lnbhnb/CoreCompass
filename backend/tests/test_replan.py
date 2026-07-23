import pytest
from unittest.mock import patch
from app.services import project_service, replan_service
from app import models
from app.state_machine import TaskStatus

FALLBACK_PLAN = {
    "milestones": [
        {"name": "M1", "expected_artifact_type": "md", "tasks": [
            {"title": "core task", "priority": "core", "est_effort_days": 3.0, "week": 1},
            {"title": "opt task A", "priority": "optional", "est_effort_days": 2.0, "week": 1},
            {"title": "opt task B", "priority": "optional", "est_effort_days": 1.0, "week": 1}]}]}


@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
def test_capacity_calc_no_gap(mock_llm):
    pid = project_service.create_project_with_plan("p", "2026-12-31", 3, "t")
    tasks = models.list_tasks_by_project(pid)
    gap = replan_service.calculate_gap(tasks, remaining_days=60, team_size=3)
    assert gap <= 0


@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
def test_capacity_calc_with_gap(mock_llm):
    pid = project_service.create_project_with_plan("p", "2026-12-31", 3, "t")
    tasks = models.list_tasks_by_project(pid)
    gap = replan_service.calculate_gap(tasks, remaining_days=1, team_size=1)
    assert gap > 0


@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
@patch("app.services.replan_service.client.generate_replan_proposal")
def test_replan_cannot_cut_core(mock_proposal, mock_init):
    """铁律：即使 LLM 试图砍 core，系统也不允许"""
    pid = project_service.create_project_with_plan("p", "2026-12-31", 3, "t")
    tasks = models.list_tasks_by_project(pid)
    core_id = [t for t in tasks if t["priority"] == "core"][0]["id"]
    mock_proposal.return_value = {
        "cut_tasks": [core_id], "downgrade_tasks": [], "rationale": "wrong"}
    proposal = replan_service.propose_replan(pid, remaining_days=1, team_size=1)
    replan_service.apply_replan(pid, proposal["proposal"], remaining_days=1, team_size=1)
    assert models.get_task(core_id)["status"] != "cut"
    cut_tasks = [t for t in models.list_tasks_by_project(pid, include_cut=True)
                 if t["status"] == "cut"]
    assert len(cut_tasks) >= 1
    assert all(t["priority"] == "optional" for t in cut_tasks)
