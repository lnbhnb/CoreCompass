from fastapi import HTTPException
from app.services import auth_service


def get_current_user(token: str | None = None) -> dict:
    """token 无效或为空 → 401。"""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="token 无效")
    return user


def require_member(project_id: int, user: dict):
    """非项目成员 → 403。"""
    from app import models
    if not models.get_project_member(project_id, user["id"]):
        raise HTTPException(status_code=403, detail="非项目成员")
    return user


def require_leader(project_id: int, user: dict):
    """非队长 → 403。"""
    from app import models
    member = models.get_project_member(project_id, user["id"])
    if not member:
        raise HTTPException(status_code=403, detail="非项目成员")
    if member["role"] != "leader":
        raise HTTPException(status_code=403, detail="需要队长权限")
    return user
