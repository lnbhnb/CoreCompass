from datetime import datetime, timedelta
from app import models
from app.llm import client


def create_project_with_plan(name, deadline, team_size, topic_desc):
    pid = models.create_project(name, deadline, team_size, topic_desc)
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
    return pid


def get_project_detail(pid):
    return {
        "project": models.get_project(pid),
        "milestones": models.list_milestones(pid),
        "tasks": models.list_tasks_by_project(pid)}
