from fastapi import APIRouter, Header
from app.services import member_service
from app import models, deps

router = APIRouter()


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


@router.post("/api/projects/{pid}/invites")
def create_invite(pid: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    deps.require_leader(pid, user)
    return member_service.generate_invite(pid, token)


@router.get("/api/projects/{pid}/members")
def list_members(pid: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    deps.require_member(pid, user)
    return models.list_project_members(pid)


@router.get("/api/projects/{pid}/progress")
def get_progress(pid: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    deps.require_member(pid, user)
    progress = member_service.get_member_progress(pid)
    member = models.get_project_member(pid, user["id"])
    if member and member["role"] != "leader":
        progress["members"] = [m for m in progress["members"] if m["user"]["id"] == user["id"]]
        progress["pending_review"] = []
    return progress
