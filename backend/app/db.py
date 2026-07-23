import sqlite3
from pathlib import Path
from app import config


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    with get_conn() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
