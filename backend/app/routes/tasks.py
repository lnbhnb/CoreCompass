from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import models
from app.state_machine import TaskStatus, transition_task, InvalidTransition
from datetime import datetime

router = APIRouter()


class CheckinReq(BaseModel):
    note: str = ""


class StatusUpdate(BaseModel):
    event: str  # start | complete | overdue


@router.post("/api/tasks/{task_id}/checkin")
def checkin(task_id: int, req: CheckinReq):
    models.insert_checkin(task_id, req.note)
    return {"ok": True}


@router.patch("/api/tasks/{task_id}/status")
def update_status(task_id: int, req: StatusUpdate):
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    try:
        new_status = transition_task(TaskStatus(task["status"]), req.event)
    except InvalidTransition as e:
        raise HTTPException(400, str(e))
    completed_at = datetime.now().isoformat() if new_status == TaskStatus.DONE else None
    models.update_task_status(task_id, new_status.value, completed_at)
    return {"task_id": task_id, "status": new_status.value}
