from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app.services import project_service
from app import models, deps

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    deadline: str
    team_size: int
    topic_desc: str


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


def _current_user(authorization: str | None):
    return deps.get_current_user(_extract_token(authorization))


@router.post("/api/projects")
def create_project(req: ProjectCreate, authorization: str | None = Header(None)):
    user = _current_user(authorization)
    try:
        result = project_service.create_project_with_plan(
            req.name, req.deadline, req.team_size, req.topic_desc, creator_id=user["id"])
        pid = result["project_id"]
        detail = project_service.get_project_detail(pid)
        detail["used_references"] = result["used_references"]
        detail["current_role"] = "leader"
        return {"project_id": pid, "detail": detail}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects")
def list_projects(authorization: str | None = Header(None)):
    user = _current_user(authorization)
    return models.list_projects_for_user(user["id"])


@router.get("/api/projects/{pid}")
def get_project(pid: int, authorization: str | None = Header(None)):
    user = _current_user(authorization)
    deps.require_member(pid, user)
    detail = project_service.get_project_detail(pid)
    member = models.get_project_member(pid, user["id"])
    detail["current_role"] = member["role"] if member else None
    return detail
