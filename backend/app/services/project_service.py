from datetime import datetime, timedelta
from app import models
from app.llm import client
from app.services import knowledge_service


def create_project_with_plan(name, deadline, team_size, topic_desc):
    pid = models.create_project(name, deadline, team_size, topic_desc)

    # 匹配知识库素材
    refs = knowledge_service.match_references(topic_desc)
    kb_context = knowledge_service.build_prompt_context(refs)

    # 调用 LLM（有素材用带素材的 prompt，无素材用原 prompt）
    if kb_context:
        plan = client.generate_initial_plan_with_kb(
            topic=topic_desc, team_size=team_size,
            deadline=deadline, kb_context=kb_context)
    else:
        plan = client.generate_initial_plan(topic_desc, team_size, deadline)

    for idx, ms in enumerate(plan.get("milestones", [])):
        mid = models.create_milestone(
            pid, ms["name"], idx, ms.get("expected_artifact_type", "other"))
        for t in ms.get("tasks", []):
            week = t.get("week", idx + 1)
            t_start = datetime.now() + timedelta(weeks=week - 1)
            t_due = t_start + timedelta(days=7)
            models.create_task(
                milestone_id=mid, project_id=pid,
                title=t["title"], description=t.get("description", ""),
                priority=t.get("priority", "optional"),
                difficulty=t.get("difficulty", "mid"),
                est_effort_days=t.get("est_effort_days", 1.0),
                start_date=t_start.isoformat(),
                due_date=t_due.isoformat())
    return {"project_id": pid, "used_references": refs}


def get_project_detail(pid):
    return {
        "project": models.get_project(pid),
        "milestones": models.list_milestones(pid),
        "tasks": models.list_tasks_by_project(pid)}
