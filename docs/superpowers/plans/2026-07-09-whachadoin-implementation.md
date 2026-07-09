# whachadoin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `whachadoin` — a personal work-log + todo tracker with a `kwd` CLI (Typer) and a Textual TUI, storing linked todos and log entries in a single SQLite file.

**Architecture:** A `src/` layout package `whachadoin` with four modules: `models.py` (Pydantic row models), `db.py` (path resolution, stdlib `sqlite3` connection, schema, CRUD — the single source of writes), `cli.py` (Typer app `app`, console command `kwd`), and `tui.py` (Textual app calling the same `db.py` functions). Marking a todo done is the one cross-table write: it updates the todo and inserts a linked log row.

**Tech Stack:** Python 3.13, uv-managed. `typer` (CLI), `pydantic` (validation), `textual` (TUI), stdlib `sqlite3` (no ORM). `pytest` (dev) for `db.py`/`models.py`.

## Global Constraints

Every task implicitly includes these. Copied verbatim from the design spec and task brief:

- **Python 3.13**, project is **uv-managed**. Add runtime deps with `uv add typer pydantic textual`; add dev deps with `uv add --dev pytest`.
- **Always run via `uv run`.** A hook BLOCKS bare `python` / `pytest`. Never invoke them directly — use `uv run python …`, `uv run pytest …`, `uv run kwd …`.
- **`src/` layout:** package lives at `src/whachadoin/`. `pyproject.toml` must declare a build backend and point the wheel at `src/whachadoin`.
- **Console command is `kwd`:** `pyproject.toml` → `[project.scripts]` → `kwd = "whachadoin.cli:app"`. The Typer app object MUST be named `app` in `cli.py`.
- **Remove the placeholder `main.py`** at repo root.
- **Storage:** stdlib `sqlite3`, **no ORM**. One DB file, two tables `todos` + `log`. Pydantic models validate rows in and out.
- **Status** is a `Literal["open","done"]` — validation lives in the model, not the DB.
- **All timestamps** are ISO 8601, UTC, generated inside `db.py`.
- **Schema init is idempotent** (`CREATE TABLE IF NOT EXISTS`), run on every connection open.
- **DB path resolution order:** explicit `--db` / `db_path` arg → `WHACHADOIN_DB` env → `$XDG_DATA_HOME/whachadoin/log.db` (if `XDG_DATA_HOME` set) → `~/.whachadoin/log.db`. Create the parent dir on first use. No `platformdirs` dependency.
- **Errors** (bad id, empty text) exit non-zero with a one-line message; `db.py` raises `ValueError`, `cli.py` catches and prints.
- **Out of scope (YAGNI):** tags, full-text search, edit/delete, recurring todos, multi-user, sync, config file.

## File Structure

- `pyproject.toml` — deps, src-layout build config, `kwd` script entry. (modify)
- `src/whachadoin/__init__.py` — package marker, empty. (create)
- `src/whachadoin/models.py` — `Todo`, `LogEntry` Pydantic models. (create)
- `src/whachadoin/db.py` — path resolution, `connect`, schema, all CRUD. (create)
- `src/whachadoin/cli.py` — Typer `app`, `kwd` commands. (create)
- `src/whachadoin/tui.py` — Textual app + `run()`. (create)
- `tests/test_db.py` — models, path resolution, CRUD, linkage. (create)
- `main.py` — DELETE.

---

## Task 1: Project scaffold, dependencies, src layout

Convert the uv scaffold to a src-layout package with the `kwd` entry point and the three runtime deps + pytest. No application logic yet — deliverable is an importable package and a resolvable (empty) `kwd` command.

**Files:**
- Modify: `pyproject.toml`
- Create: `src/whachadoin/__init__.py`
- Create: `src/whachadoin/cli.py` (minimal placeholder so `kwd` resolves)
- Delete: `main.py`

**Interfaces:**
- Produces: importable package `whachadoin`; `whachadoin.cli:app` (a `typer.Typer` instance) usable as the `kwd` console script.

- [ ] **Step 1: Add runtime and dev dependencies via uv**

```bash
cd /home/user/projects/whachadoin
uv add typer pydantic textual
uv add --dev pytest
```

Expected: `uv` resolves and writes them into `pyproject.toml` `[project.dependencies]` and a `[dependency-groups] dev` (or `[tool.uv] dev-dependencies`) list, and updates `uv.lock`.

- [ ] **Step 2: Remove the placeholder entry file**

```bash
rm /home/user/projects/whachadoin/main.py
```

- [ ] **Step 3: Create the package directory with an empty `__init__.py`**

```bash
mkdir -p /home/user/projects/whachadoin/src/whachadoin
mkdir -p /home/user/projects/whachadoin/tests
```

Create `src/whachadoin/__init__.py` with a single line:

```python
"""whachadoin — work log + todo CLI/TUI."""
```

- [ ] **Step 4: Create a minimal `cli.py` so the entry point resolves**

Create `src/whachadoin/cli.py`:

```python
"""Typer CLI for whachadoin. Console command: kwd."""
from __future__ import annotations

import typer

app = typer.Typer(help="whachadoin — work log + todo tracker", no_args_is_help=True)
```

- [ ] **Step 5: Set the build backend, src layout, and `kwd` script in `pyproject.toml`**

Edit `pyproject.toml` so it reads (keep the `dependencies` / dev group that `uv add` wrote; add the marked sections). The full file should look like:

```toml
[project]
name = "whachadoin"
version = "0.1.0"
description = "Personal work-log and todo tracker (CLI + TUI)"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "typer",
    "pydantic",
    "textual",
]

[project.scripts]
kwd = "whachadoin.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/whachadoin"]

[dependency-groups]
dev = [
    "pytest",
]
```

Note: if `uv add --dev` wrote `[tool.uv] dev-dependencies` instead of `[dependency-groups]`, leave whichever form uv produced — do not duplicate. The load-bearing additions are `[project.scripts]`, `[build-system]`, and `[tool.hatch.build.targets.wheel]`.

- [ ] **Step 6: Verify the package imports and the entry point resolves**

```bash
cd /home/user/projects/whachadoin
uv run python -c "import whachadoin; import whachadoin.cli; print('ok')"
uv run kwd --help
```

Expected: first prints `ok`; second prints Typer help text and exits 0.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: scaffold src-layout package, deps, and kwd entry point"
```

---

## Task 2: Pydantic row models

Define `Todo` and `LogEntry`, mirroring the two tables. Status validation (open/done) lives here.

**Files:**
- Create: `src/whachadoin/models.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces:
  - `Todo(BaseModel)` fields: `id: Optional[int] = None`, `text: str`, `status: Literal["open","done"] = "open"`, `priority: int = 0`, `created_at: str`, `done_at: Optional[str] = None`
  - `LogEntry(BaseModel)` fields: `id: Optional[int] = None`, `ts: str`, `text: str`, `todo_id: Optional[int] = None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_db.py` with:

```python
import pytest
from pydantic import ValidationError

from whachadoin.models import Todo, LogEntry


def test_todo_defaults_and_valid_status():
    t = Todo(text="write plan", created_at="2026-07-09T00:00:00+00:00")
    assert t.id is None
    assert t.status == "open"
    assert t.priority == 0
    assert t.done_at is None


def test_todo_rejects_bad_status():
    with pytest.raises(ValidationError):
        Todo(text="x", status="finished", created_at="2026-07-09T00:00:00+00:00")


def test_logentry_defaults():
    e = LogEntry(ts="2026-07-09T00:00:00+00:00", text="did a thing")
    assert e.id is None
    assert e.todo_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'whachadoin.models'`.

- [ ] **Step 3: Write the models**

Create `src/whachadoin/models.py`:

```python
"""Pydantic models mirroring the todos and log tables."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class Todo(BaseModel):
    id: Optional[int] = None
    text: str
    status: Literal["open", "done"] = "open"
    priority: int = 0
    created_at: str
    done_at: Optional[str] = None


class LogEntry(BaseModel):
    id: Optional[int] = None
    ts: str
    text: str
    todo_id: Optional[int] = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/whachadoin/models.py tests/test_db.py
git commit -m "feat: add Todo and LogEntry pydantic models"
```

---

## Task 3: DB path resolution

Resolve the SQLite path from override → env → XDG → home, with no external deps. Independently testable without opening a DB.

**Files:**
- Create: `src/whachadoin/db.py`
- Test: `tests/test_db.py` (append)

**Interfaces:**
- Produces:
  - `default_db_path() -> pathlib.Path` — `$XDG_DATA_HOME/whachadoin/log.db` if `XDG_DATA_HOME` set, else `~/.whachadoin/log.db`.
  - `resolve_db_path(override: str | os.PathLike | None = None) -> pathlib.Path` — precedence: `override` → `WHACHADOIN_DB` env → `default_db_path()`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db.py`:

```python
from pathlib import Path

from whachadoin import db as dbmod


def test_default_path_uses_xdg_when_set(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg")
    assert dbmod.default_db_path() == Path("/tmp/xdg/whachadoin/log.db")


def test_default_path_falls_back_to_home(monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/tester")))
    assert dbmod.default_db_path() == Path("/home/tester/.whachadoin/log.db")


def test_resolve_precedence(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg")
    monkeypatch.setenv("WHACHADOIN_DB", "/tmp/env.db")
    # explicit override wins over env and default
    assert dbmod.resolve_db_path("/tmp/explicit.db") == Path("/tmp/explicit.db")
    # env wins over default
    assert dbmod.resolve_db_path(None) == Path("/tmp/env.db")
    # default used when neither given
    monkeypatch.delenv("WHACHADOIN_DB", raising=False)
    assert dbmod.resolve_db_path(None) == Path("/tmp/xdg/whachadoin/log.db")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db.py -k "path or resolve or precedence" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'whachadoin.db'`.

- [ ] **Step 3: Write path-resolution code**

Create `src/whachadoin/db.py`:

```python
"""SQLite storage: path resolution, connection, schema, and CRUD."""
from __future__ import annotations

import os
from pathlib import Path


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS (all tests so far).

- [ ] **Step 5: Commit**

```bash
git add src/whachadoin/db.py tests/test_db.py
git commit -m "feat: resolve DB path from override, env, XDG, or home"
```

---

## Task 4: Connection, schema, and CRUD

Add the connection opener (idempotent schema init), and all CRUD functions. Marking a todo done is the single cross-table write: update the row and insert a linked log entry.

**Files:**
- Modify: `src/whachadoin/db.py`
- Test: `tests/test_db.py` (append)

**Interfaces:**
- Consumes: `resolve_db_path` (Task 3); `Todo`, `LogEntry` (Task 2).
- Produces (all raise `ValueError` on bad input as noted):
  - `connect(db_path: str | os.PathLike | None = None) -> sqlite3.Connection` — resolves path, creates parent dir, opens with `row_factory = sqlite3.Row`, runs idempotent schema, returns the connection.
  - `add_todo(conn, text: str, priority: int = 0) -> Todo` — raises `ValueError` on empty text.
  - `list_todos(conn, include_done: bool = False) -> list[Todo]` — open-only by default; sorted `priority DESC, created_at ASC`.
  - `get_todo(conn, todo_id: int) -> Todo | None`
  - `done_todo(conn, todo_id: int) -> Todo` — raises `ValueError` if id missing; sets `status='done'`, `done_at=now`, inserts linked log row; returns the updated todo.
  - `add_log(conn, text: str, todo_id: int | None = None) -> LogEntry` — raises `ValueError` on empty text.
  - `list_log(conn, today: bool = False, since: str | None = None) -> list[LogEntry]` — newest first (`ts DESC, id DESC`); `today` restricts to the current UTC date; `since` is a `YYYY-MM-DD` lower bound.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_db.py`:

```python
@pytest.fixture
def conn(tmp_path):
    c = dbmod.connect(tmp_path / "log.db")
    yield c
    c.close()


def test_connect_creates_parent_dir(tmp_path):
    target = tmp_path / "nested" / "dir" / "log.db"
    c = dbmod.connect(target)
    c.close()
    assert target.exists()


def test_add_and_list_todo(conn):
    t = dbmod.add_todo(conn, "buy milk", priority=2)
    assert t.id is not None
    assert t.status == "open"
    todos = dbmod.list_todos(conn)
    assert [x.text for x in todos] == ["buy milk"]


def test_list_todos_sorted_by_priority_then_created(conn):
    dbmod.add_todo(conn, "low", priority=0)
    dbmod.add_todo(conn, "high", priority=5)
    dbmod.add_todo(conn, "mid", priority=1)
    assert [t.text for t in dbmod.list_todos(conn)] == ["high", "mid", "low"]


def test_add_todo_rejects_empty_text(conn):
    with pytest.raises(ValueError):
        dbmod.add_todo(conn, "   ")


def test_done_todo_links_log_entry(conn):
    t = dbmod.add_todo(conn, "ship it")
    updated = dbmod.done_todo(conn, t.id)
    assert updated.status == "done"
    assert updated.done_at is not None
    entries = dbmod.list_log(conn)
    assert len(entries) == 1
    assert entries[0].todo_id == t.id


def test_done_missing_todo_raises(conn):
    with pytest.raises(ValueError):
        dbmod.done_todo(conn, 999)


def test_list_todos_excludes_done_by_default(conn):
    t = dbmod.add_todo(conn, "done soon")
    dbmod.done_todo(conn, t.id)
    assert dbmod.list_todos(conn) == []
    assert len(dbmod.list_todos(conn, include_done=True)) == 1


def test_add_log_freestanding(conn):
    e = dbmod.add_log(conn, "read the spec")
    assert e.id is not None
    assert e.todo_id is None
    assert dbmod.list_log(conn)[0].text == "read the spec"


def test_add_log_rejects_empty_text(conn):
    with pytest.raises(ValueError):
        dbmod.add_log(conn, "")


def test_list_log_since_filter(conn):
    dbmod.add_log(conn, "old")  # today's entry
    # a since date in the future excludes everything
    assert dbmod.list_log(conn, since="2999-01-01") == []
    # a since date in the past includes it
    assert len(dbmod.list_log(conn, since="2000-01-01")) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_db.py -v`
Expected: FAIL — `AttributeError: module 'whachadoin.db' has no attribute 'connect'`.

- [ ] **Step 3: Implement connection, schema, and CRUD**

Add to the top imports of `src/whachadoin/db.py` (alongside the existing `os` / `Path` imports):

```python
import sqlite3
from datetime import datetime, timezone

from .models import LogEntry, Todo
```

Append to `src/whachadoin/db.py`:

```python
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
```

Note on the `since`/`today` filter: `ts` is a full ISO timestamp (e.g. `2026-07-09T21:31:00+00:00`); comparing it against a bare `YYYY-MM-DD` string works because the date prefix sorts lexicographically ahead of that day's `T…` times. `# ponytail: string date compare, fine for ISO-8601; revisit only if timezone-local filtering is ever needed.`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add src/whachadoin/db.py tests/test_db.py
git commit -m "feat: add sqlite connection, schema, and CRUD with todo-done linkage"
```

---

## Task 5: Typer CLI (`kwd`)

Replace the placeholder `cli.py` with the full command surface. `db.py` raises `ValueError`; the CLI catches it, prints a one-line message, and exits non-zero. No automated CLI tests (per spec) — verify by invocation.

**Files:**
- Modify: `src/whachadoin/cli.py`

**Interfaces:**
- Consumes: `db.connect`, `db.add_todo`, `db.list_todos`, `db.done_todo`, `db.add_log`, `db.list_log` (Task 4).
- Produces: Typer `app` with commands — `log` (insert, or `log ls` to list), `todo add`, `todo done`, `todo ls`, `tui`. A top-level `--db` option overrides the DB path.

**Design note (Typer positional-vs-subcommand conflict):** The spec asks for both `kwd log "text"` (a positional) and `kwd log ls` (a listing verb). Click/Typer cannot have a group with BOTH a positional argument AND a real subcommand — a declared positional consumes the token before subcommand resolution. So `log` is implemented as a single command that takes a variadic `words` argument and dispatches internally: if the first word is `ls`, it lists; otherwise it joins the words and inserts a log entry. `# ponytail: "ls" is a reserved first word for the log command; logging the literal message "ls" is not supported, which the spec already treats as the list verb.` `todo` has no positional-vs-subcommand conflict, so it is a normal Typer sub-app with `add` / `done` / `ls`.

- [ ] **Step 1: Write the full CLI**

Replace the entire contents of `src/whachadoin/cli.py` with:

```python
"""Typer CLI for whachadoin. Console command: kwd."""
from __future__ import annotations

from typing import List, Optional

import typer

from . import db as dbmod

app = typer.Typer(help="whachadoin — work log + todo tracker", no_args_is_help=True)
todo_app = typer.Typer(help="manage todos", no_args_is_help=True)
app.add_typer(todo_app, name="todo")


@app.callback()
def _main(
    ctx: typer.Context,
    db: Optional[str] = typer.Option(None, "--db", help="override the DB path"),
) -> None:
    """Store the optional DB override for subcommands to read."""
    ctx.obj = db


def _fail(message: str) -> None:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(1)


@app.command()
def log(
    ctx: typer.Context,
    words: Optional[List[str]] = typer.Argument(
        None, help='log text, or "ls" to list entries'
    ),
    today: bool = typer.Option(False, "--today", help="ls: only today's entries"),
    since: Optional[str] = typer.Option(
        None, "--since", help="ls: entries since YYYY-MM-DD"
    ),
) -> None:
    """Add a log entry, or `kwd log ls` to list entries newest-first."""
    conn = dbmod.connect(ctx.obj)
    words = list(words or [])
    if words and words[0] == "ls":
        for e in dbmod.list_log(conn, today=today, since=since):
            link = f" (todo #{e.todo_id})" if e.todo_id else ""
            typer.echo(f"{e.ts}  {e.text}{link}")
        return
    text = " ".join(words).strip()
    try:
        entry = dbmod.add_log(conn, text)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"logged #{entry.id}")


@todo_app.command("add")
def todo_add(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="todo text"),
    priority: int = typer.Option(0, "--priority", help="higher = more urgent"),
) -> None:
    """Add an open todo."""
    conn = dbmod.connect(ctx.obj)
    try:
        todo = dbmod.add_todo(conn, text, priority=priority)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"added todo #{todo.id}")


@todo_app.command("done")
def todo_done(
    ctx: typer.Context,
    todo_id: int = typer.Argument(..., help="id of the todo to complete"),
) -> None:
    """Mark a todo done and record a linked log entry."""
    conn = dbmod.connect(ctx.obj)
    try:
        todo = dbmod.done_todo(conn, todo_id)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"done: #{todo.id} {todo.text}")


@todo_app.command("ls")
def todo_ls(
    ctx: typer.Context,
    all_: bool = typer.Option(False, "--all", help="include done todos"),
) -> None:
    """List open todos (--all includes done), priority desc then created."""
    conn = dbmod.connect(ctx.obj)
    for t in dbmod.list_todos(conn, include_done=all_):
        typer.echo(f"#{t.id}  p{t.priority}  {t.status:<4}  {t.text}")


@app.command()
def tui(ctx: typer.Context) -> None:
    """Launch the Textual TUI."""
    from .tui import run

    run(ctx.obj)
```

Note: `tui` imports `.tui` lazily so the rest of the CLI works before Task 6 lands and so importing `cli` never forces Textual to load.

- [ ] **Step 2: Verify commands work end-to-end against a temp DB**

```bash
cd /home/user/projects/whachadoin
export WHACHADOIN_DB="$(mktemp -d)/log.db"
uv run kwd todo add "write the code" --priority 3
uv run kwd todo add "read the spec"
uv run kwd todo ls
uv run kwd todo done 1
uv run kwd todo ls --all
uv run kwd log "started refactor"
uv run kwd log ls
uv run kwd log ls --today
uv run kwd todo done 999; echo "exit=$?"
unset WHACHADOIN_DB
```

Expected: adds print `added todo #1` / `#2`; `todo ls` lists both open (priority 3 first); after `done 1`, plain `todo ls` shows only `#2`, `--all` shows both with `#1 done`; `log ls` shows the linked "completed todo #1" entry plus "started refactor", newest first; `done 999` prints `error: no todo with id 999` to stderr and `exit=1`.

- [ ] **Step 3: Commit**

```bash
git add src/whachadoin/cli.py
git commit -m "feat: implement kwd CLI (log, todo add/done/ls, tui)"
```

---

## Task 6: Textual TUI

Single-screen TUI: left pane todos, right pane log feed, footer input, keybinds. Writes go through the same `db.py` functions, then both panes refresh. No automated tests (spec: manual) — verify by launching.

**Files:**
- Create: `src/whachadoin/tui.py`

**Interfaces:**
- Consumes: `db.connect`, `db.add_todo`, `db.add_log`, `db.done_todo`, `db.list_todos`, `db.list_log` (Task 4).
- Produces: `run(db_override: str | None = None) -> None` — builds and runs the app (called by `cli.tui`).

- [ ] **Step 1: Write the TUI**

Create `src/whachadoin/tui.py`:

```python
"""Textual TUI for whachadoin: todos + log feed, single screen."""
from __future__ import annotations

from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView

from . import db as dbmod


class WhachadoinApp(App):
    CSS = """
    #panes { height: 1fr; }
    #todos, #logs { width: 1fr; border: round $primary; }
    #entry { dock: bottom; }
    """

    BINDINGS = [
        Binding("a", "add_todo", "Add todo"),
        Binding("l", "add_log", "Add log"),
        Binding("d", "done", "Mark done"),
        Binding("r", "refresh_panes", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, db_override: Optional[str] = None) -> None:
        super().__init__()
        self.conn = dbmod.connect(db_override)
        self.todo_ids: List[int] = []
        self.input_mode: Optional[str] = None  # "todo" | "log"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panes"):
            yield ListView(id="todos")
            yield ListView(id="logs")
        yield Input(placeholder="press a to add todo, l to add log", id="entry")
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh_panes()

    def action_refresh_panes(self) -> None:
        todos = self.query_one("#todos", ListView)
        todos.clear()
        self.todo_ids = []
        for t in dbmod.list_todos(self.conn):
            self.todo_ids.append(t.id)
            todos.append(ListItem(Label(f"#{t.id} (p{t.priority}) {t.text}")))
        logs = self.query_one("#logs", ListView)
        logs.clear()
        for e in dbmod.list_log(self.conn):
            logs.append(ListItem(Label(f"{e.ts[:16]}  {e.text}")))

    def _prompt(self, mode: str, placeholder: str) -> None:
        self.input_mode = mode
        entry = self.query_one("#entry", Input)
        entry.placeholder = placeholder
        entry.value = ""
        entry.focus()

    def action_add_todo(self) -> None:
        self._prompt("todo", "new todo text, then Enter")

    def action_add_log(self) -> None:
        self._prompt("log", "new log entry, then Enter")

    def action_done(self) -> None:
        todos = self.query_one("#todos", ListView)
        idx = todos.index
        if idx is None or idx >= len(self.todo_ids):
            return
        dbmod.done_todo(self.conn, self.todo_ids[idx])
        self.action_refresh_panes()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        mode, self.input_mode = self.input_mode, None
        event.input.value = ""
        if not text or mode is None:
            return
        if mode == "todo":
            dbmod.add_todo(self.conn, text)
        elif mode == "log":
            dbmod.add_log(self.conn, text)
        self.action_refresh_panes()


def run(db_override: Optional[str] = None) -> None:
    WhachadoinApp(db_override).run()
```

- [ ] **Step 2: Manual smoke test**

```bash
cd /home/user/projects/whachadoin
export WHACHADOIN_DB="$(mktemp -d)/log.db"
uv run kwd tui
# In the app: press `a`, type a todo, Enter → appears left.
# Press `l`, type a note, Enter → appears right.
# Select a todo, press `d` → moves out of open list, a "completed" entry appears right.
# Press `q` to quit.
unset WHACHADOIN_DB
```

Expected: app launches, all keybinds behave as described, no traceback on quit.

- [ ] **Step 3: Full test suite still green**

Run: `uv run pytest -v`
Expected: PASS (all `tests/test_db.py`).

- [ ] **Step 4: Commit**

```bash
git add src/whachadoin/tui.py
git commit -m "feat: add Textual TUI wired to shared db functions"
```

---

## Self-Review

**Spec coverage:**
- Stack / layout / `[project.scripts] kwd` — Task 1. ✅
- Data model (two tables, schema, link on done) — Task 4 (`SCHEMA`, `done_todo`). ✅
- Pydantic models incl. `Literal` status — Task 2. ✅
- DB path resolution (override → env → XDG → home, parent dir) — Task 3 + `connect` in Task 4. ✅
- CLI commands (`log`, `log ls`, `todo add/done/ls`, `tui`) with non-zero error exits — Task 5. ✅
- TUI (two panes, footer input, keybinds a/l/d/r/q, shared db funcs) — Task 6. ✅
- Timestamps ISO-8601 UTC in `db.py`; idempotent schema per connect — Task 4. ✅
- Testing (CRUD round trips, done linkage, Pydantic validation, path resolution via override) — Tasks 2–4. ✅
- Out-of-scope items — not implemented, as intended. ✅

**Placeholder scan:** No TBD/TODO/"add error handling" placeholders; every code step is complete.

**Type consistency:** `connect`, `add_todo`, `list_todos`, `get_todo`, `done_todo`, `add_log`, `list_log` signatures match between the db.py implementation (Task 4), the CLI consumer (Task 5), the TUI consumer (Task 6), and the Interfaces blocks. `Todo`/`LogEntry` field names match the SQL columns used in `Todo(**dict(row))` / `LogEntry(**dict(row))`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-09-whachadoin-implementation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.
