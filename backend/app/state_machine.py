from enum import Enum


class TaskStatus(str, Enum):
    PLANNED = "planned"
    DOING = "doing"
    DONE = "done"
    OVERDUE = "overdue"
    CUT = "cut"


class MilestoneStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    LOCKED = "locked"
    DONE = "done"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    CRISIS = "crisis"
    COMPLETED = "completed"


class InvalidTransition(Exception):
    pass


_TASK = {
    TaskStatus.PLANNED: {"start": TaskStatus.DOING, "cut": TaskStatus.CUT},
    TaskStatus.DOING: {"complete": TaskStatus.DONE, "overdue": TaskStatus.OVERDUE, "cut": TaskStatus.CUT},
    TaskStatus.OVERDUE: {"complete": TaskStatus.DONE, "cut": TaskStatus.CUT},
    TaskStatus.DONE: {},
    TaskStatus.CUT: {},
}

_MILESTONE = {
    MilestoneStatus.PLANNED: {"start": MilestoneStatus.IN_PROGRESS},
    MilestoneStatus.IN_PROGRESS: {"lock": MilestoneStatus.LOCKED, "complete": MilestoneStatus.DONE},
    MilestoneStatus.LOCKED: {"unlock": MilestoneStatus.IN_PROGRESS, "complete": MilestoneStatus.DONE},
    MilestoneStatus.DONE: {},
}

_PROJECT = {
    ProjectStatus.ACTIVE: {"crisis": ProjectStatus.CRISIS, "complete": ProjectStatus.COMPLETED},
    ProjectStatus.CRISIS: {"resolve": ProjectStatus.ACTIVE, "complete": ProjectStatus.COMPLETED},
    ProjectStatus.COMPLETED: {},
}


def transition_task(current, event):
    allowed = _TASK.get(current, {})
    if event not in allowed:
        raise InvalidTransition(f"任务 {current.value} 不允许事件 {event}")
    return allowed[event]


def transition_milestone(current, event):
    allowed = _MILESTONE.get(current, {})
    if event not in allowed:
        raise InvalidTransition(f"里程碑 {current.value} 不允许事件 {event}")
    return allowed[event]


def transition_project(current, event):
    allowed = _PROJECT.get(current, {})
    if event not in allowed:
        raise InvalidTransition(f"项目 {current.value} 不允许事件 {event}")
    return allowed[event]
