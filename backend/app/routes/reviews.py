from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services import review_service
from app import deps, models
from pathlib import Path
from datetime import datetime

router = APIRouter()


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


class AssignReq(BaseModel):
    assignee_id: int


class ReviewReq(BaseModel):
    decision: str  # approved | rejected
    comment: str | None = None


def _get_task_or_404(task_id):
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.post("/api/tasks/{task_id}/assign")
def assign(task_id: int, req: AssignReq, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_leader(task["project_id"], user)
    review_service.assign_task(task_id, req.assignee_id, token, task["project_id"])
    return {"ok": True}


@router.post("/api/tasks/{task_id}/claim")
def claim(task_id: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_member(task["project_id"], user)
    try:
        review_service.claim_task(task_id, token, task["project_id"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.post("/api/tasks/{task_id}/submit")
async def submit(task_id: int, file: UploadFile = File(...), authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_member(task["project_id"], user)
    upload_dir = Path("data/submissions")
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_name = f"{task_id}_{int(datetime.now().timestamp())}_{file.filename}"
    save_path = upload_dir / save_name
    save_path.write_bytes(await file.read())
    review_service.submit_task(task_id, file.filename, str(save_path), token, task["project_id"])
    return {"ok": True, "filename": file.filename}


@router.post("/api/tasks/{task_id}/review")
def review(task_id: int, req: ReviewReq, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_leader(task["project_id"], user)
    review_service.review_task(task_id, req.decision, token, task["project_id"], req.comment)
    return {"ok": True}


@router.get("/api/tasks/{task_id}/submission")
def download_submission(task_id: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_member(task["project_id"], user)
    if not task.get("submission_path"):
        raise HTTPException(404, "无提交产物")
    pm = models.get_project_member(task["project_id"], user["id"])
    if pm["role"] != "leader" and task["assignee_id"] != user["id"]:
        raise HTTPException(403, "无权下载")
    return FileResponse(task["submission_path"], filename=task["submission_filename"])
