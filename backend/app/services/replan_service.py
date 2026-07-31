import json
from datetime import datetime, timedelta
from app import models
from app.llm import client
from app.state_machine import TaskStatus, transition_task, ProjectStatus

EFFICIENCY_FACTOR = 0.6


def _build_human_summary(gap, capacity, remaining_days, team_size,
                          cut_titles, cut_saved, downgrade_titles, downgrade_saved, final_gap):
    """生成拟人化重规划总结，避免"人天"等技术黑话。"""
    gap_r = round(gap)
    cap_r = round(capacity)
    lines = []

    # 缺口
    if gap_r <= 3:
        lines.append(f"还差大约 {gap_r} 天的工作量，不算严重")
    elif gap_r <= 10:
        lines.append(f"目前还差大约 {gap_r} 天的工作量")
    else:
        lines.append(f"工作量缺口比较大，大约差 {gap_r} 天")

    # 团队产能
    lines.append(f"你们 {team_size} 个人还剩 {remaining_days} 天，全力以赴大概能产出 {cap_r} 天的工作量")

    # 砍任务
    if cut_titles:
        names = "、".join(f"「{t}」" for t in cut_titles)
        lines.append(f"建议砍掉 {names}，可以省出大约 {round(cut_saved)} 天")

    # 降级
    if downgrade_titles:
        names = "、".join(f"「{t}」" for t in downgrade_titles)
        lines.append(f"建议把 {names} 做得简单一点，能省大约 {round(downgrade_saved)} 天")

    # 结果
    if abs(final_gap) <= 0.5:
        lines.append("调整之后工作量刚好匹配，可以按时交付 ✅")
    elif final_gap < 0:
        lines.append("调整之后绰绰有余，稳了 💪")
    else:
        lines.append(f"调整后还差大约 {round(final_gap)} 天，不过已经在可控范围内了")

    return "\n".join(lines)


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

    # ============ 用代码算结构化文案（不再依赖 LLM 写散文）============
    capacity = round(remaining_days * team_size * EFFICIENCY_FACTOR, 2)

    # 砍任务节省
    cut_saved = 0.0
    cut_titles = []
    for tid in proposal.get("cut_tasks", []):
        t = models.get_task(tid)
        if t:
            cut_saved += t["est_effort_days"]
            cut_titles.append(t["title"])

    # 降级任务节省
    downgrade_saved = 0.0
    downgrade_titles = []
    for d in proposal.get("downgrade_tasks", []):
        tid = d.get("id")
        old_effort = d.get("old_effort", 0)
        new_effort = d.get("new_effort", 0)
        downgrade_saved += max(0, old_effort - new_effort)
        t = models.get_task(tid)
        if t:
            downgrade_titles.append(t["title"])

    # 构建结构化步骤（每步带数字，永远准确）
    rationale_steps = []
    remaining = round(gap, 2)
    if cut_titles:
        rationale_steps.append({
            "step": len(rationale_steps) + 1,
            "action": f"砍掉 {len(cut_titles)} 个 optional 任务",
            "tasks": cut_titles,
            "saved_days": round(cut_saved, 2),
            "gap_after": round(remaining - cut_saved, 2),
        })
    if downgrade_titles:
        rationale_steps.append({
            "step": len(rationale_steps) + 1,
            "action": f"降级 {len(downgrade_titles)} 个 core 任务难度",
            "tasks": downgrade_titles,
            "saved_days": round(downgrade_saved, 2),
            "gap_after": round(remaining - cut_saved - downgrade_saved, 2),
        })
    final_gap = round(remaining - cut_saved - downgrade_saved, 2)
    rationale_steps.append({
        "step": len(rationale_steps) + 1,
        "action": f"剩余工作量 {final_gap} 人天 ≈ 团队产能 {capacity} 人天",
        "match": abs(final_gap) <= 0.1,
        "team_capacity": capacity,
    })

    # ============ 构建拟人化总结文案 ============
    summary = _build_human_summary(gap, capacity, remaining_days, team_size,
                                   cut_titles, cut_saved, downgrade_titles, downgrade_saved, final_gap)

    proposal["summary"] = summary
    proposal["capacity"] = round(capacity, 1)
    proposal["cut_details"] = [{"title": t, "saved": round(cut_saved, 1)} for t in cut_titles] if cut_titles else []
    proposal["downgrade_details"] = [{"title": t, "saved": round(downgrade_saved, 1)} for t in downgrade_titles] if downgrade_titles else []

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
