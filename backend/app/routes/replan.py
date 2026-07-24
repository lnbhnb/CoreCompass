from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
from app.services import replan_service
from app import models, deps
from app.db import get_conn

router = APIRouter()


class ReplanApply(BaseModel):
    proposal: dict


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


@router.post("/api/replan/{pid}/propose")
def propose(pid: int, authorization: str | None = Header(None)):
    user = deps.get_current_user(_token(authorization))
    deps.require_member(pid, user)
    project = models.get_project(pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    deadline_dt = datetime.fromisoformat(project["deadline"])
    remaining_days = max(0, (deadline_dt - datetime.now()).days)
    return replan_service.propose_replan(pid, remaining_days, project["team_size"])


@router.post("/api/replan/{pid}/apply")
def apply(pid: int, req: ReplanApply, authorization: str | None = Header(None)):
    user = deps.get_current_user(_token(authorization))
    deps.require_member(pid, user)
    project = models.get_project(pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    deadline_dt = datetime.fromisoformat(project["deadline"])
    remaining_days = max(0, (deadline_dt - datetime.now()).days)
    return replan_service.apply_replan(pid, req.proposal, remaining_days, project["team_size"])


@router.post("/api/replan/{pid}/trigger_overdue")
def trigger_overdue(pid: int, authorization: str | None = Header(None)):
    """手动将 doing 任务标记为 overdue（Demo 模拟偏航用）。"""
    user = deps.get_current_user(_token(authorization))
    deps.require_member(pid, user)
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tasks SET status='overdue' WHERE project_id=? AND status='doing'",
            (pid,))
        affected = cur.rowcount
    return {
        "affected": affected,
        "message": f"已将 {affected} 个进行中任务标记为逾期" if affected else "当前没有进行中的任务可标记"
    }
