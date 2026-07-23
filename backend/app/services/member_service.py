import secrets
import string
from datetime import datetime, timedelta
from app import models
from app.services import auth_service


def generate_invite(project_id, leader_token):
    """队长生成 6 位邀请码，7 天有效。权限校验由路由层做。"""
    leader = auth_service.get_user_by_token(leader_token)
    if not leader:
        raise ValueError("无效 token")
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    expires_at = (datetime.now() + timedelta(days=7)).isoformat()
    models.create_invite(project_id, code, expires_at)
    return {"code": code, "expires_at": expires_at}


def join_with_code(code, member_token):
    """队员用邀请码加入项目。已是成员则幂等返回，不消耗码。"""
    member = auth_service.get_user_by_token(member_token)
    if not member:
        raise ValueError("无效 token")
    invite = models.get_invite_by_code(code)
    if not invite:
        raise ValueError("邀请码不存在")
    if invite["used_by_user_id"]:
        raise ValueError("邀请码已被使用")
    if datetime.fromisoformat(invite["expires_at"]) < datetime.now():
        raise ValueError("邀请码已过期")
    # 幂等：已是成员直接返回，不消耗码
    existing = models.get_project_member(invite["project_id"], member["id"])
    if existing:
        return {"project_id": invite["project_id"]}
    models.add_project_member(invite["project_id"], member["id"], "member")
    models.mark_invite_used(invite["id"], member["id"])
    return {"project_id": invite["project_id"]}


def get_member_progress(project_id):
    """返回项目每个成员的进度统计 + 待审阅任务列表。"""
    members = models.list_project_members(project_id)
    tasks = models.list_tasks_by_project(project_id)
    result = []
    for m in members:
        my_tasks = [t for t in tasks if t.get("assignee_id") == m["id"]]
        done = sum(1 for t in my_tasks if t["status"] == "done")
        pending_review = sum(1 for t in my_tasks if t.get("review_status") == "pending_review")
        todo = sum(1 for t in my_tasks if t["status"] in ("planned", "doing"))
        total = len(my_tasks)
        pct = round(done / total * 100) if total else 0
        result.append({
            "user": {"id": m["id"], "username": m["username"], "display_name": m["display_name"]},
            "role": m["role"],
            "total": total, "done": done,
            "pending_review": pending_review, "todo": todo,
            "percent": pct,
            "tasks": my_tasks})
    pending = [t for t in tasks if t.get("review_status") == "pending_review"]
    return {"members": result, "pending_review": pending}
