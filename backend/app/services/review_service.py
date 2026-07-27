from datetime import datetime

from app import models
from app.services import auth_service, notify_service
from app.state_machine import MilestoneStatus, ProjectStatus


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
    assignee_member = models.get_project_member(project_id, assignee_id)
    if not assignee_member:
        raise PermissionError("被分配人不是项目成员")
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


def unclaim_task(task_id, member_token, project_id):
    """取消认领。仅允许 assignee 本人或队长操作，且仅限 planned 状态的任务。"""
    user = _user_from_token(member_token)
    member = models.get_project_member(project_id, user["id"])
    if not member:
        raise PermissionError("非项目成员")
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    if task["status"] != "planned":
        raise PermissionError("仅未开始的任务可取消认领")
    if task["assignee_id"] is None:
        raise PermissionError("任务未被认领")
    is_assignee = task["assignee_id"] == user["id"]
    is_leader = member["role"] == "leader"
    if not is_assignee and not is_leader:
        raise PermissionError("仅任务负责人或队长可取消认领")
    models.unassign_task(task_id)


def submit_task(task_id, filename, filepath, member_token, project_id):
    member = _user_from_token(member_token)
    _require_member(project_id, member)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    if task["assignee_id"] != member["id"]:
        raise PermissionError("只有任务负责人能提交")
    models.submit_task(task_id, filename, filepath)
    # 提交后自动推进到 doing（如果还是 planned）
    if task["status"] == "planned":
        models.update_task_status(task_id, "doing")
    content = f"{member['display_name']} 提交了任务「{task['title']}」，待审阅"
    _notify(project_id, "task_submit", content)


def review_task(task_id, decision, leader_token, project_id, comment=None):
    leader = _user_from_token(leader_token)
    _require_leader(project_id, leader)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    if task.get("review_status") != "pending_review":
        raise PermissionError("当前任务不在待审阅状态")
    models.review_task(task_id, decision, leader["id"], comment)
    # 通过 → 任务 done + 推进里程碑
    if decision == "approved":
        if task["status"] != "done":
            models.update_task_status(task_id, "done", datetime.now().isoformat())
        advance_milestone_if_complete(project_id, task["milestone_id"])
    # 打回 → 任务回退到 doing（队员需修改后重新提交）
    else:
        if task["status"] == "done":
            models.update_task_status(task_id, "doing")
    # 通知：写 DB + 推飞书
    verb = "已通过" if decision == "approved" else "需修改"
    content = f"任务「{task['title']}」{verb}"
    if comment:
        content += f"：{comment}"
    _notify(project_id, "task_review", content)


def _notify(project_id, ntype, content):
    """通知：写 DB + 推送飞书（webhook 未配则仅写 DB）。"""
    models.insert_notification(project_id, ntype, content, "sent", None)
    try:
        notify_service.send_feishu(content, project_id=project_id, msg_type=ntype)
    except Exception:
        pass  # 飞书不可达不影响主流程


def advance_milestone_if_complete(project_id: int, milestone_id: int):
    """检查里程碑下所有非 cut 任务是否全部 done，如是则推进里程碑→done。
    如所有里程碑 done，则推进项目→completed。"""
    tasks = models.list_tasks_by_milestone(milestone_id)
    active = [t for t in tasks if t["status"] != "cut"]
    if not active:
        return  # 没有活跃任务，不推进

    all_done = all(t["status"] == "done" for t in active)
    if not all_done:
        return

    ms = models.get_milestone(milestone_id)
    if ms and ms["status"] != MilestoneStatus.DONE.value:
        models.update_milestone_status(milestone_id, MilestoneStatus.DONE.value)

    # 检查项目级：所有里程碑 done → 项目 completed
    all_ms = models.list_milestones(project_id)
    if all(m["status"] == MilestoneStatus.DONE.value for m in all_ms):
        models.update_project_status(project_id, ProjectStatus.COMPLETED.value)
