from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app import models, deps
from app.state_machine import TaskStatus, transition_task, InvalidTransition
from datetime import datetime

router = APIRouter()


class CheckinReq(BaseModel):
    note: str = ""


class StatusUpdate(BaseModel):
    event: str  # start | complete | overdue


class TaskCreateReq(BaseModel):
    title: str


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


@router.post("/api/tasks/{task_id}/checkin")
def checkin(task_id: int, req: CheckinReq, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    deps.require_member(task["project_id"], user)
    models.insert_checkin(task_id, req.note)
    return {"ok": True}


@router.patch("/api/tasks/{task_id}/status")
def update_status(task_id: int, req: StatusUpdate, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    deps.require_member(task["project_id"], user)
    member = models.get_project_member(task["project_id"], user["id"])
    if member["role"] != "leader" and task.get("assignee_id") != user["id"]:
        raise HTTPException(403, "只有任务负责人或队长可改状态")
    try:
        new_status = transition_task(TaskStatus(task["status"]), req.event)
    except InvalidTransition as e:
        raise HTTPException(400, str(e))
    completed_at = datetime.now().isoformat() if new_status == TaskStatus.DONE else None
    models.update_task_status(task_id, new_status.value, completed_at)
    return {"task_id": task_id, "status": new_status.value}


@router.post("/api/milestones/{mid}/tasks")
def create_task_endpoint(mid: int, req: TaskCreateReq, authorization: str | None = Header(None)):
    """队长手动新增任务节点（仅填标题，其余字段默认）"""
    token = _token(authorization)
    user = deps.get_current_user(token)
    ms = models.get_milestone(mid)
    if not ms:
        raise HTTPException(404, "里程碑不存在")
    deps.require_leader(ms["project_id"], user)
    now = datetime.now().isoformat()
    task_id = models.create_task(
        milestone_id=mid, project_id=ms["project_id"],
        title=req.title, description="", priority="optional",
        difficulty="mid", est_effort_days=1.0,
        start_date=now, due_date=None
    )
    return {"task_id": task_id, "id": task_id}


@router.delete("/api/tasks/{task_id}")
def delete_task_endpoint(task_id: int, authorization: str | None = Header(None)):
    """队长删除任务节点（仅限 planned 状态）"""
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    deps.require_leader(task["project_id"], user)
    if task["status"] != "planned":
        raise HTTPException(400, "仅未开始的任务可删除")
    models.delete_task(task_id)
    return {"ok": True}
