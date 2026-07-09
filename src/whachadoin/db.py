"""SQLite storage: path resolution, connection, schema, and CRUD."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import LogEntry, Todo


def default_db_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "whachadoin" / "log.db"
    return Path.home() / ".whachadoin" / "log.db"


def resolve_db_path(override: str | os.PathLike | None = None) -> Path:
    if override:
        return Path(override)
    env = os.environ.get("WHACHADOIN_DB")
    if env:
        return Path(env)
    return default_db_path()


SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
  id         INTEGER PRIMARY KEY,
  text       TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'open',
  priority   INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  done_at    TEXT
);
CREATE TABLE IF NOT EXISTS log (
  id      INTEGER PRIMARY KEY,
  ts      TEXT NOT NULL,
  text    TEXT NOT NULL,
  todo_id INTEGER REFERENCES todos(id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str | os.PathLike | None = None) -> sqlite3.Connection:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def add_todo(conn: sqlite3.Connection, text: str, priority: int = 0) -> Todo:
    text = text.strip()
    if not text:
        raise ValueError("todo text must not be empty")
    todo = Todo(text=text, priority=priority, created_at=_now())
    cur = conn.execute(
        "INSERT INTO todos (text, status, priority, created_at, done_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (todo.text, todo.status, todo.priority, todo.created_at, todo.done_at),
    )
    conn.commit()
    todo.id = cur.lastrowid
    return todo


def get_todo(conn: sqlite3.Connection, todo_id: int) -> Todo | None:
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return Todo(**dict(row)) if row else None


def list_todos(conn: sqlite3.Connection, include_done: bool = False) -> list[Todo]:
    sql = "SELECT * FROM todos"
    if not include_done:
        sql += " WHERE status = 'open'"
    sql += " ORDER BY priority DESC, created_at ASC"
    return [Todo(**dict(r)) for r in conn.execute(sql)]


def done_todo(conn: sqlite3.Connection, todo_id: int) -> Todo:
    todo = get_todo(conn, todo_id)
    if todo is None:
        raise ValueError(f"no todo with id {todo_id}")
    if todo.status == "done":
        # ponytail: already done, return as-is rather than double-log
        return todo
    now = _now()
    conn.execute(
        "UPDATE todos SET status = 'done', done_at = ? WHERE id = ?", (now, todo_id)
    )
    conn.execute(
        "INSERT INTO log (ts, text, todo_id) VALUES (?, ?, ?)",
        (now, f"completed todo #{todo_id}: {todo.text}", todo_id),
    )
    conn.commit()
    return get_todo(conn, todo_id)


def add_log(
    conn: sqlite3.Connection, text: str, todo_id: int | None = None
) -> LogEntry:
    text = text.strip()
    if not text:
        raise ValueError("log text must not be empty")
    entry = LogEntry(ts=_now(), text=text, todo_id=todo_id)
    cur = conn.execute(
        "INSERT INTO log (ts, text, todo_id) VALUES (?, ?, ?)",
        (entry.ts, entry.text, entry.todo_id),
    )
    conn.commit()
    entry.id = cur.lastrowid
    return entry


def list_log(
    conn: sqlite3.Connection, today: bool = False, since: str | None = None
) -> list[LogEntry]:
    if today:
        since = datetime.now(timezone.utc).date().isoformat()
    sql = "SELECT * FROM log"
    params: list[str] = []
    if since:
        sql += " WHERE ts >= ?"
        params.append(since)
    sql += " ORDER BY ts DESC, id DESC"
    return [LogEntry(**dict(r)) for r in conn.execute(sql, params)]
