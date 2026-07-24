from datetime import datetime, timedelta
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


def delete_task(task_id):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))


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


def delete_project(pid):
    """硬删除项目。依赖 schema 的 ON DELETE CASCADE 级联清理 milestones/tasks/members 等。"""
    with db.get_conn() as conn:
        conn.execute("DELETE FROM projects WHERE id=?", (pid,))


def update_project_notify_config(pid, webhook_url, secret):
    """更新项目级飞书 webhook 配置。传 None 清空字段。"""
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE projects SET feishu_webhook_url=?, feishu_secret=? WHERE id=?",
            (webhook_url, secret, pid))


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


# ============ 用户与认证 ============
def create_user(username, password_hash, display_name, token, token_expires_at=None):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users(username, password_hash, display_name, token, token_expires_at) VALUES(?,?,?,?,?)",
            (username, password_hash, display_name, token, token_expires_at))
        return cur.lastrowid


def get_user_by_username(username):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_token(token):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
        return dict(row) if row else None


def get_user(uid):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(row) if row else None


def clear_user_token(uid):
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET token=NULL, token_expires_at=NULL WHERE id=?", (uid,))


# ============ 项目成员 ============
def add_project_member(project_id, user_id, role):
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO project_members(project_id, user_id, role) VALUES(?,?,?)",
            (project_id, user_id, role))


def get_project_member(project_id, user_id):
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM project_members WHERE project_id=? AND user_id=?",
            (project_id, user_id)).fetchone()
        return dict(row) if row else None


def list_project_members(project_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT pm.role, pm.joined_at, u.id, u.username, u.display_name
               FROM project_members pm JOIN users u ON pm.user_id=u.id
               WHERE pm.project_id=? ORDER BY pm.joined_at""",
            (project_id,)).fetchall()
        return [dict(r) for r in rows]


def list_projects_for_user(user_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT p.* FROM projects p
               JOIN project_members pm ON pm.project_id=p.id
               WHERE pm.user_id=? ORDER BY p.id DESC""",
            (user_id,)).fetchall()
        return [dict(r) for r in rows]


def set_project_creator(project_id, user_id):
    with db.get_conn() as conn:
        conn.execute("UPDATE projects SET creator_id=? WHERE id=?", (user_id, project_id))


# ============ 邀请码 ============
def create_invite(project_id, code, expires_at):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO invite_codes(project_id, code, expires_at) VALUES(?,?,?)",
            (project_id, code, expires_at))
        return cur.lastrowid


def get_invite_by_code(code):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM invite_codes WHERE code=?", (code,)).fetchone()
        return dict(row) if row else None


def mark_invite_used(invite_id, user_id):
    with db.get_conn() as conn:
        conn.execute("UPDATE invite_codes SET used_by_user_id=? WHERE id=?", (user_id, invite_id))


def increment_invite_fail(invite_id, lock_minutes=15):
    """邀请码失败计数 +1，达到阈值锁定。返回当前 fail_count。"""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT fail_count FROM invite_codes WHERE id=?", (invite_id,)).fetchone()
        if not row:
            return 0
        new_count = row["fail_count"] + 1
        if new_count >= 5:
            locked_until = (datetime.now() + timedelta(minutes=lock_minutes)).isoformat()
            conn.execute(
                "UPDATE invite_codes SET fail_count=?, locked_until=? WHERE id=?",
                (new_count, locked_until, invite_id))
        else:
            conn.execute(
                "UPDATE invite_codes SET fail_count=? WHERE id=?", (new_count, invite_id))
        return new_count


def reset_invite_fail(invite_id):
    """成功加入后清零失败计数。"""
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE invite_codes SET fail_count=0, locked_until=NULL WHERE id=?", (invite_id,))


def list_active_invites_for_project(project_id):
    """列出项目下未使用且未过期的邀请码，按创建时间倒序。"""
    from datetime import datetime
    now_iso = datetime.now().isoformat()
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT id, code, expires_at, created_at FROM invite_codes
               WHERE project_id=? AND used_by_user_id IS NULL AND expires_at >= ?
               ORDER BY id DESC""",
            (project_id, now_iso)).fetchall()
        return [dict(r) for r in rows]


# ============ 任务审阅 ============
def assign_task(task_id, assignee_id):
    with db.get_conn() as conn:
        conn.execute("UPDATE tasks SET assignee_id=? WHERE id=?", (assignee_id, task_id))


def submit_task(task_id, submission_filename, submission_path):
    with db.get_conn() as conn:
        conn.execute(
            """UPDATE tasks SET submission_filename=?, submission_path=?,
               review_status='pending_review' WHERE id=?""",
            (submission_filename, submission_path, task_id))


def review_task(task_id, decision, reviewer_id, comment=None):
    """decision: 'approved' | 'rejected'"""
    from datetime import datetime
    conn_status = "approved" if decision == "approved" else "rejected"
    with db.get_conn() as conn:
        conn.execute(
            """UPDATE tasks SET review_status=?, reviewed_by=?, reviewed_at=?, review_comment=?
               WHERE id=?""",
            (conn_status, reviewer_id, datetime.now().isoformat(), comment, task_id))
