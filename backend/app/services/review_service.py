from app import models
from app.services import auth_service


def _user_from_token(token):
    user = auth_service.get_user_by_token(token)
    if not user:
        raise PermissionError("无效 token")
    return user


def _require_leader(project_id, user):
    member = models.get_project_member(project_id, user["id"])
    if not member:
        raise PermissionError("非项目成员")
    if member["role"] != "leader":
        raise PermissionError("需要队长权限")


def _require_member(project_id, user):
    member = models.get_project_member(project_id, user["id"])
    if not member:
        raise PermissionError("非项目成员")


def assign_task(task_id, assignee_id, leader_token, project_id):
    leader = _user_from_token(leader_token)
    _require_leader(project_id, leader)
    models.assign_task(task_id, assignee_id)


def claim_task(task_id, member_token, project_id):
    member = _user_from_token(member_token)
    _require_member(project_id, member)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    if task["assignee_id"] is not None:
        raise ValueError("任务已被认领")
    models.assign_task(task_id, member["id"])


def submit_task(task_id, filename, filepath, member_token, project_id):
    member = _user_from_token(member_token)
    _require_member(project_id, member)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    if task["assignee_id"] != member["id"]:
        raise PermissionError("只有任务负责人能提交")
    models.submit_task(task_id, filename, filepath)
    _notify_leader(project_id, "task_submit",
                   f"{member['display_name']} 提交了任务 {task['title']}，待审阅")


def review_task(task_id, decision, leader_token, project_id, comment=None):
    leader = _user_from_token(leader_token)
    _require_leader(project_id, leader)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    models.review_task(task_id, decision, leader["id"], comment)
    if task.get("assignee_id"):
        assignee = models.get_user(task["assignee_id"])
        if assignee:
            verb = "已通过" if decision == "approved" else "需修改"
            content = f"任务 {task['title']} {verb}"
            if comment:
                content += f"：{comment}"
            # 复用现有 insert_notification(pid, type, content, status, response) 签名
            models.insert_notification(project_id, "task_review", content, "sent", None)


def _notify_leader(project_id, ntype, content):
    members = models.list_project_members(project_id)
    for m in members:
        if m["role"] == "leader":
            models.insert_notification(project_id, ntype, content, "sent", None)
            break
