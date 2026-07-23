import json
from datetime import datetime, timedelta
from app import models
from app.llm import client
from app.state_machine import TaskStatus, transition_task, ProjectStatus

EFFICIENCY_FACTOR = 0.6


def calculate_gap(tasks, remaining_days, team_size):
    remaining_work = sum(t["est_effort_days"] for t in tasks
                         if t["status"] in ("planned", "doing", "overdue"))
    capacity = remaining_days * team_size * EFFICIENCY_FACTOR
    return round(remaining_work - capacity, 2)


def propose_replan(project_id, remaining_days, team_size):
    tasks = models.list_tasks_by_project(project_id)
    gap = calculate_gap(tasks, remaining_days, team_size)
    if gap <= 0:
        return {"gap_days": gap, "proposal": None, "action": "no_action",
                "message": "产能充足，无需砍需求"}
    project = models.get_project(project_id)
    if project["status"] != ProjectStatus.CRISIS.value:
        models.update_project_status(project_id, ProjectStatus.CRISIS.value)
    tasks_for_llm = [{"id": t["id"], "title": t["title"], "priority": t["priority"],
                      "difficulty": t["difficulty"],
                      "est_effort_days": t["est_effort_days"],
                      "status": t["status"]} for t in tasks]
    proposal = client.generate_replan_proposal(
        remaining_days, team_size, gap,
        json.dumps(tasks_for_llm, ensure_ascii=False))
    models.insert_replan_log(project_id, gap,
                             json.dumps(proposal, ensure_ascii=False), False)
    return {"gap_days": gap, "proposal": proposal, "action": "propose",
            "message": f"缺口 {gap} 人天，已生成砍/降级提案"}


def apply_replan(project_id, proposal, remaining_days=None, team_size=None):
    if not proposal:
        return {"applied": False, "message": "无提案可应用"}
    cut_ids = proposal.get("cut_tasks", [])
    downgrade = proposal.get("downgrade_tasks", [])
    valid_cuts = []
    for tid in cut_ids:
        task = models.get_task(tid)
        if task and task["priority"] == "optional":
            new_status = transition_task(TaskStatus(task["status"]), "cut")
            models.update_task_status(tid, new_status.value)
            valid_cuts.append(tid)
    for d in downgrade:
        tid = d.get("id")
        task = models.get_task(tid)
        if not task:
            continue
        models.update_task(tid,
                           difficulty=d.get("to", task["difficulty"]),
                           est_effort_days=d.get("new_effort", task["est_effort_days"] * 0.6))
    # 保底：若仍有缺口，强制砍难度最高的 optional
    project = models.get_project(project_id)
    if remaining_days is None:
        deadline_dt = datetime.fromisoformat(project["deadline"])
        remaining_days = max(0, (deadline_dt - datetime.now()).days)
    if team_size is None:
        team_size = project["team_size"]
    remaining_tasks = models.list_tasks_by_project(project_id)
    gap = calculate_gap(remaining_tasks, remaining_days, team_size)
    if gap > 0:
        optional_undoing = [t for t in remaining_tasks
                            if t["priority"] == "optional"
                            and t["status"] in ("planned", "doing", "overdue")]
        if optional_undoing:
            optional_undoing.sort(key=lambda t: t["est_effort_days"], reverse=True)
            t = optional_undoing[0]
            new_status = transition_task(TaskStatus(t["status"]), "cut")
            models.update_task_status(t["id"], new_status.value)
            valid_cuts.append(t["id"])
    # 重排剩余任务日期
    remaining = models.list_tasks_by_project(project_id)
    remaining.sort(key=lambda t: t.get("due_date") or "")
    today = datetime.now()
    n = max(1, len(remaining))
    for i, t in enumerate(remaining):
        new_due = today + timedelta(days=(i + 1) * max(1, remaining_days // n))
        models.update_task(t["id"], due_date=new_due.isoformat())
    models.update_project_status(project_id, ProjectStatus.ACTIVE.value)
    models.insert_replan_log(project_id, gap,
                             json.dumps(proposal, ensure_ascii=False), True)
    return {"applied": True, "cut_task_ids": valid_cuts,
            "downgrade_count": len(downgrade), "remaining_gap": gap}
