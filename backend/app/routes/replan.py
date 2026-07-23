from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.services import replan_service
from app import models
from app.db import get_conn

router = APIRouter()


class ReplanApply(BaseModel):
    proposal: dict


@router.post("/api/replan/{pid}/propose")
def propose(pid: int):
    project = models.get_project(pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    deadline_dt = datetime.fromisoformat(project["deadline"])
    remaining_days = max(0, (deadline_dt - datetime.now()).days)
    return replan_service.propose_replan(pid, remaining_days, project["team_size"])


@router.post("/api/replan/{pid}/apply")
def apply(pid: int, req: ReplanApply):
    project = models.get_project(pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    deadline_dt = datetime.fromisoformat(project["deadline"])
    remaining_days = max(0, (deadline_dt - datetime.now()).days)
    return replan_service.apply_replan(pid, req.proposal, remaining_days, project["team_size"])


@router.post("/api/replan/{pid}/trigger_overdue")
def trigger_overdue(pid: int):
    """手动将 doing 任务标记为 overdue（Demo 模拟偏航用）"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status='overdue' WHERE project_id=? AND status='doing'",
            (pid,))
    return {"message": "已将所有 doing 任务标记为 overdue"}
