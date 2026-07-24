import sqlite3
from pathlib import Path
from app import config


# 轻量协作版字段迁移（幂等：列已存在则跳过）
FIELD_MIGRATIONS = [
    "ALTER TABLE projects ADD COLUMN creator_id INTEGER REFERENCES users(id)",
    "ALTER TABLE tasks ADD COLUMN assignee_id INTEGER REFERENCES users(id)",
    "ALTER TABLE tasks ADD COLUMN review_status TEXT",
    "ALTER TABLE tasks ADD COLUMN submission_filename TEXT",
    "ALTER TABLE tasks ADD COLUMN submission_path TEXT",
    "ALTER TABLE tasks ADD COLUMN reviewed_by INTEGER REFERENCES users(id)",
    "ALTER TABLE tasks ADD COLUMN reviewed_at TEXT",
    "ALTER TABLE tasks ADD COLUMN review_comment TEXT",
    # 安全加固迁移（token 过期 + 邀请码防爆破）
    "ALTER TABLE users ADD COLUMN token_expires_at TEXT",
    "ALTER TABLE invite_codes ADD COLUMN fail_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE invite_codes ADD COLUMN locked_until TEXT",
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    with get_conn() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        for sql in FIELD_MIGRATIONS:
            try:
                conn.execute(sql)
            except Exception:
                pass  # 列已存在
        conn.commit()
