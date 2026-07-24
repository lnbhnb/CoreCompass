from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app.services import project_service, notify_service
from app import models, deps

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    deadline: str
    team_size: int
    topic_desc: str


class ProjectNotifyConfig(BaseModel):
    feishu_webhook_url: str | None = None
    feishu_secret: str | None = None


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


@router.delete("/api/projects/{pid}")
def delete_project(pid: int, authorization: str | None = Header(None)):
    """队长硬删除项目。级联清理所有关联数据；删除前向飞书推送解散通知。"""
    user = _current_user(authorization)
    deps.require_leader(pid, user)

    project = models.get_project(pid)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 删除前先收集成员信息用于通知文案
    members = models.list_project_members(pid)
    has_other_members = any(m["id"] != user["id"] for m in members)

    # 先推送飞书通知（notifications 记录会随级联删除一起清理）
    if has_other_members:
        notify_text = f"🚢 项目《{project['name']}》已被队长解散，感谢各位船员的一路同行。"
        try:
            notify_service.send_feishu(notify_text, project_id=pid, msg_type="project_dissolved")
        except Exception:
            pass  # 通知失败不阻塞删除

    models.delete_project(pid)
    return {"deleted": pid}


@router.patch("/api/projects/{pid}")
def update_project_notify_config(pid: int, req: ProjectNotifyConfig,
                                  authorization: str | None = Header(None)):
    """队长更新项目的飞书通知配置（项目级 webhook，一项目一群）。"""
    user = _current_user(authorization)
    deps.require_leader(pid, user)
    models.update_project_notify_config(pid, req.feishu_webhook_url, req.feishu_secret)
    return {"updated": pid}
