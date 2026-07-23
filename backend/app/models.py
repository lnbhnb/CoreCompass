from app import db


def create_project(name, deadline, team_size, topic_desc):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO projects(name, deadline, team_size, topic_desc) VALUES(?,?,?,?)",
            (name, deadline, team_size, topic_desc))
        return cur.lastrowid


def get_project(pid):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None


def list_projects():
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()]


def create_milestone(project_id, name, order_idx, expected_artifact_type):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO milestones(project_id, name, order_idx, expected_artifact_type) VALUES(?,?,?,?)",
            (project_id, name, order_idx, expected_artifact_type))
        return cur.lastrowid


def create_task(milestone_id, project_id, title, description, priority, difficulty,
                est_effort_days, start_date, due_date):
    with db.get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tasks(milestone_id, project_id, title, description, priority,
               difficulty, est_effort_days, start_date, due_date) VALUES(?,?,?,?,?,?,?,?,?)""",
            (milestone_id, project_id, title, description, priority, difficulty,
             est_effort_days, start_date, due_date))
        return cur.lastrowid


def get_task(task_id):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None


def get_milestone(mid):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM milestones WHERE id=?", (mid,)).fetchone()
        return dict(row) if row else None


def list_milestones(pid):
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM milestones WHERE project_id=? ORDER BY order_idx", (pid,)).fetchall()]


def list_tasks_by_project(pid, include_cut=False):
    sql = "SELECT * FROM tasks WHERE project_id=?"
    if not include_cut:
        sql += " AND status != 'cut'"
    sql += " ORDER BY due_date"
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, (pid,)).fetchall()]


def update_task_status(task_id, status, completed_at=None):
    with db.get_conn() as conn:
        conn.execute("UPDATE tasks SET status=?, completed_at=? WHERE id=?",
                     (status, completed_at, task_id))


def update_task(task_id, **fields):
    allowed = {"priority", "difficulty", "est_effort_days", "status", "due_date", "start_date"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    vals.append(task_id)
    with db.get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", vals)


def update_milestone_status(mid, status):
    with db.get_conn() as conn:
        conn.execute("UPDATE milestones SET status=? WHERE id=?", (status, mid))


def update_project_status(pid, status):
    with db.get_conn() as conn:
        conn.execute("UPDATE projects SET status=? WHERE id=?", (status, pid))


def insert_checkin(task_id, note):
    with db.get_conn() as conn:
        conn.execute("INSERT INTO checkins(task_id, note) VALUES(?,?)", (task_id, note))


def insert_validation(mid, filename, file_type, result, fail_reasons, llm_used):
    with db.get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO validation_records(milestone_id, filename, file_type, result,
               fail_reasons, llm_used) VALUES(?,?,?,?,?,?)""",
            (mid, filename, file_type, result, fail_reasons, llm_used))
        return cur.lastrowid


def insert_replan_log(pid, gap_days, proposal, applied):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO replan_logs(project_id, gap_days, proposal, applied) VALUES(?,?,?,?)",
            (pid, gap_days, proposal, applied))
        return cur.lastrowid


def insert_notification(pid, type, content, status, response):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notifications(project_id, type, content, status, response) VALUES(?,?,?,?,?)",
            (pid, type, content, status, response))
        return cur.lastrowid


def list_notifications(pid=None, limit=50):
    with db.get_conn() as conn:
        if pid:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE project_id=? ORDER BY id DESC LIMIT ?",
                (pid, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def list_overdue_tasks(pid=None):
    sql = "SELECT * FROM tasks WHERE status='overdue'"
    params = ()
    if pid:
        sql += " AND project_id=?"
        params = (pid,)
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
