import pytest
from app.state_machine import (
    transition_task, transition_milestone, transition_project,
    TaskStatus, MilestoneStatus, ProjectStatus, InvalidTransition)


def test_task_planned_to_doing():
    assert transition_task(TaskStatus.PLANNED, "start") == TaskStatus.DOING


def test_task_doing_to_done():
    assert transition_task(TaskStatus.DOING, "complete") == TaskStatus.DONE


def test_task_doing_to_overdue():
    assert transition_task(TaskStatus.DOING, "overdue") == TaskStatus.OVERDUE


def test_task_any_to_cut():
    for s in [TaskStatus.PLANNED, TaskStatus.DOING, TaskStatus.OVERDUE]:
        assert transition_task(s, "cut") == TaskStatus.CUT


def test_invalid_transition_raises():
    with pytest.raises(InvalidTransition):
        transition_task(TaskStatus.DONE, "start")


def test_milestone_lock():
    assert transition_milestone(MilestoneStatus.IN_PROGRESS, "lock") == MilestoneStatus.LOCKED


def test_project_crisis_and_back():
    assert transition_project(ProjectStatus.ACTIVE, "crisis") == ProjectStatus.CRISIS
    assert transition_project(ProjectStatus.CRISIS, "resolve") == ProjectStatus.ACTIVE
