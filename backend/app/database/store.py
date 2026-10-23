import json
import sqlite3
from contextlib import contextmanager
from app.core.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
 kind TEXT NOT NULL, id TEXT NOT NULL, project_id TEXT,
 data TEXT NOT NULL, PRIMARY KEY (kind, id)
);
CREATE INDEX IF NOT EXISTS records_project ON records(kind, project_id);
PRAGMA user_version = 1;
"""

@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with connection() as conn:
        conn.executescript(SCHEMA)

def put(kind, value):
    with connection() as conn:
        conn.execute("INSERT INTO records(kind,id,project_id,data) VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET project_id=excluded.project_id,data=excluded.data", (kind,value["id"],value.get("project_id"),json.dumps(value,ensure_ascii=False)))
    return value

def get(kind, record_id):
    with connection() as conn:
        row = conn.execute("SELECT data FROM records WHERE kind=? AND id=?",(kind,record_id)).fetchone()
    return json.loads(row[0]) if row else None

def all_records(kind, project_id=None):
    with connection() as conn:
        if project_id is None:
            rows=conn.execute("SELECT data FROM records WHERE kind=? ORDER BY rowid",(kind,)).fetchall()
        else:
            rows=conn.execute("SELECT data FROM records WHERE kind=? AND project_id=? ORDER BY rowid",(kind,project_id)).fetchall()
    return [json.loads(row[0]) for row in rows]

def remove(kind, record_id):
    with connection() as conn:
        conn.execute("DELETE FROM records WHERE kind=? AND id=?",(kind,record_id))
