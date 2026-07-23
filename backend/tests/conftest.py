import sqlite3
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema = Path(__file__).resolve().parent.parent / "app" / "schema.sql"
    conn.executescript(schema.read_text(encoding="utf-8"))
    # 与 app/db.py init_db 保持同步的字段迁移（幂等）
    from app.db import FIELD_MIGRATIONS
    for sql in FIELD_MIGRATIONS:
        try:
            conn.execute(sql)
        except Exception:
            pass
    conn.commit()
    import app.db as db
    monkeypatch.setattr(db, "get_conn", lambda: conn)
    yield conn
