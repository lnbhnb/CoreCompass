from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import project_service
from app import models

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    deadline: str
    team_size: int
    topic_desc: str


@router.post("/api/projects")
def create_project(req: ProjectCreate):
    try:
        result = project_service.create_project_with_plan(
            req.name, req.deadline, req.team_size, req.topic_desc)
        pid = result["project_id"]
        detail = project_service.get_project_detail(pid)
        detail["used_references"] = result["used_references"]
        return {"project_id": pid, "detail": detail}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects")
def list_projects():
    return models.list_projects()


@router.get("/api/projects/{pid}")
def get_project(pid: int):
    return project_service.get_project_detail(pid)
