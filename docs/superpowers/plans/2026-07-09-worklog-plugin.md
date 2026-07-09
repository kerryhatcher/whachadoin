# worklog plugin + log path/repo columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture the working directory and git repo on every `kwd` log entry, then ship a Claude Code plugin (skill + commands) so any session can drive `kwd` for logging, todos, and "what did I work on" recall.

**Architecture:** Two sequenced build parts. Part 1 changes whachadoin **core**: the `log` table gains `path` and `repo` columns, a pure-Python `find_repo()` walks up from cwd looking for `.git`, and `add_log`/`done_todo` auto-capture context. Part 2 turns the repo into an installable Claude Code **marketplace** (`.claude-plugin/marketplace.json` → one plugin under `plugin/`) carrying a trigger-phrase `worklog` skill plus `/log` and `/worklog` commands. Part 1 must land first because the plugin relies on the auto-capture behavior.

**Tech Stack:** Python 3.13, uv-managed. Core uses stdlib `sqlite3` + `pydantic` + `typer` (unchanged). The plugin is pure markdown/JSON config — no code, no new dependencies.

## Global Constraints

Every task implicitly includes these. Copied verbatim from the design spec and task brief:

- **Python 3.13**, project is **uv-managed**.
- **Always run via `uv run`.** A hook BLOCKS bare `python` / `pytest`. Never invoke them directly — use `uv run pytest …`, `uv run kwd …`.
- **Repo detection is pure Python — NO `git` subprocess.** Walk up from cwd (starting AT cwd, ascending to filesystem root); the first directory containing a `.git` file-or-directory gives `repo = basename(that dir)`; if none found, `repo = None`. (`.git` as a *file* occurs in git worktrees, so `os.path.exists` — not `is_dir` — is the check.)
- **`log` schema additions:** `path TEXT NOT NULL DEFAULT ''` and `repo TEXT` (nullable). `path` = `os.getcwd()` where `kwd` ran; `repo` = `find_repo()` result.
- **Migration is idempotent** and runs on every connection open: `CREATE TABLE IF NOT EXISTS` covers fresh DBs; for already-created DBs, read `PRAGMA table_info(log)` and `ALTER TABLE log ADD COLUMN …` only for columns that are missing.
- **Storage:** stdlib `sqlite3`, no ORM. Pydantic models validate rows in and out. Timestamps are ISO-8601 UTC generated inside `db.py`.
- **Plugin has NO hooks.** Nothing fires automatically; all capture is user-triggered.
- **Plugin keeps two todo systems separate:** `kwd` persistent cross-session todos are NOT the same as Claude Code's built-in in-session TodoWrite/Task list. Never mirror ephemeral planning items into `kwd`.
- **Out of scope (YAGNI):** path/repo on `todos`; a `--repo` filter on `kwd log ls`; auto-logging via hooks; session-start context injection; a `/todo` command.

## File Structure

**Part 1 — core (modify):**
- `src/whachadoin/models.py` — `LogEntry` gains `path` and `repo` fields.
- `src/whachadoin/db.py` — add `find_repo()`; extend `SCHEMA`; add `_migrate()` called from `connect()`; auto-capture in `add_log()` and `done_todo()`.
- `src/whachadoin/cli.py` — `kwd log ls` prints repo when present.
- `tests/test_db.py` — new tests for `find_repo`, migration, auto-capture, `LogEntry` round trip.

**Part 2 — plugin (create):**
- `.claude-plugin/marketplace.json` — repo is an installable marketplace; one plugin, `"source": "./plugin"`.
- `plugin/.claude-plugin/plugin.json` — plugin manifest.
- `plugin/skills/worklog/SKILL.md` — trigger-phrase skill driving `kwd`.
- `plugin/commands/log.md` — `/log <text>`.
- `plugin/commands/worklog.md` — `/worklog [since]`.
- `plugin/README.md` — setup prerequisites.

---

# PART 1 — whachadoin core: path + repo columns

## Task 1: `LogEntry` model gains `path` and `repo`

Add the two new fields to the Pydantic model so rows carrying them validate both ways. Defaults mirror the DB (`path=''`, `repo=None`) so existing construction sites and the current `test_logentry_defaults` keep working.

**Files:**
- Modify: `src/whachadoin/models.py`
- Test: `tests/test_db.py` (append)

**Interfaces:**
- Produces: `LogEntry(BaseModel)` with fields `id: Optional[int] = None`, `ts: str`, `text: str`, `todo_id: Optional[int] = None`, `path: str = ""`, `repo: Optional[str] = None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db.py`:

```python
def test_logentry_roundtrip_with_path_and_repo():
    e = LogEntry(
        ts="2026-07-09T00:00:00+00:00",
        text="built the TUI",
        path="/Users/x/projects/whachadoin",
        repo="whachadoin",
    )
    assert e.path == "/Users/x/projects/whachadoin"
    assert e.repo == "whachadoin"
    # defaults still hold when omitted
    d = LogEntry(ts="2026-07-09T00:00:00+00:00", text="note")
    assert d.path == ""
    assert d.repo is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db.py::test_logentry_roundtrip_with_path_and_repo -v`
Expected: FAIL — `TypeError`/`ValidationError`: `LogEntry` has no field `path`.

- [ ] **Step 3: Add the fields**

In `src/whachadoin/models.py`, replace the `LogEntry` class with:

```python
class LogEntry(BaseModel):
    id: Optional[int] = None
    ts: str
    text: str
    todo_id: Optional[int] = None
    path: str = ""
    repo: Optional[str] = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS (new test plus the pre-existing suite stay green).

- [ ] **Step 5: Commit**

```bash
git add src/whachadoin/models.py tests/test_db.py
git commit -m "feat: add path and repo fields to LogEntry model"
```

---

## Task 2: `find_repo()` walk-up helper

Add a pure-Python helper in `db.py` that finds the nearest ancestor directory (including the start dir) containing a `.git` entry and returns its basename, else `None`. No `git` subprocess.

**Files:**
- Modify: `src/whachadoin/db.py`
- Test: `tests/test_db.py` (append)

**Interfaces:**
- Produces: `find_repo(start: str | os.PathLike | None = None) -> str | None` — walks from `start` (default `os.getcwd()`) up to the filesystem root; returns `os.path.basename` of the first directory that contains a `.git` file or directory, else `None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db.py`:

```python
def test_find_repo_cwd_has_git(tmp_path):
    (tmp_path / ".git").mkdir()
    assert dbmod.find_repo(tmp_path) == tmp_path.name


def test_find_repo_nested_finds_ancestor(tmp_path):
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    assert dbmod.find_repo(nested) == tmp_path.name


def test_find_repo_git_as_file_worktree(tmp_path):
    # git worktrees store .git as a FILE, not a directory
    (tmp_path / ".git").write_text("gitdir: /somewhere/.git/worktrees/x\n")
    assert dbmod.find_repo(tmp_path) == tmp_path.name


def test_find_repo_none_in_chain(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert dbmod.find_repo(nested) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db.py -k find_repo -v`
Expected: FAIL — `AttributeError: module 'whachadoin.db' has no attribute 'find_repo'`.

- [ ] **Step 3: Implement `find_repo`**

In `src/whachadoin/db.py`, add after the `resolve_db_path` function:

```python
def find_repo(start: str | os.PathLike | None = None) -> str | None:
    """Name of the git repo containing `start` (default cwd), or None.

    Walks up from `start` looking for a `.git` file-or-directory. Uses
    os.path.exists (not is_dir) so worktrees — where `.git` is a file — match.
    No `git` subprocess.
    """
    d = Path(start) if start is not None else Path.cwd()
    d = d.resolve()
    for candidate in (d, *d.parents):
        if (candidate / ".git").exists():
            return candidate.name
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db.py -k find_repo -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/whachadoin/db.py tests/test_db.py
git commit -m "feat: add pure-python find_repo walk-up helper"
```

---

## Task 3: Schema columns + idempotent migration

Extend the `log` table definition with `path`/`repo`, and add a migration that adds those columns to already-created DBs. The migration runs inside `connect()` on every open and is safe to repeat.

**Files:**
- Modify: `src/whachadoin/db.py`
- Test: `tests/test_db.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `_migrate(conn: sqlite3.Connection) -> None` — reads `PRAGMA table_info(log)` and runs `ALTER TABLE log ADD COLUMN …` for any of `path`/`repo` that are missing. Called by `connect()` after `executescript(SCHEMA)`. Fresh DBs get the columns from `SCHEMA`; old-shape DBs get them via `_migrate`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_db.py`:

```python
import sqlite3


def test_fresh_db_has_path_and_repo_columns(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(log)")}
    assert {"path", "repo"} <= cols


def test_migration_adds_columns_to_old_shape_db(tmp_path):
    # Build an OLD-shape log table by hand (no path/repo).
    target = tmp_path / "old.db"
    raw = sqlite3.connect(str(target))
    raw.executescript(
        """
        CREATE TABLE log (
          id INTEGER PRIMARY KEY,
          ts TEXT NOT NULL,
          text TEXT NOT NULL,
          todo_id INTEGER
        );
        """
    )
    raw.execute(
        "INSERT INTO log (ts, text, todo_id) VALUES (?, ?, ?)",
        ("2026-07-09T00:00:00+00:00", "legacy row", None),
    )
    raw.commit()
    raw.close()

    # Opening via the app migrates it.
    conn = dbmod.connect(target)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(log)")}
    assert {"path", "repo"} <= cols
    old = dbmod.list_log(conn)[0]
    assert old.text == "legacy row"
    assert old.path == ""
    assert old.repo is None
    conn.close()

    # Second open is a no-op (migration is idempotent).
    conn2 = dbmod.connect(target)
    assert len(dbmod.list_log(conn2)) == 1
    conn2.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_db.py -k "columns or migration" -v`
Expected: FAIL — fresh DB lacks the columns and `list_log` on the old-shape DB errors on the missing fields.

- [ ] **Step 3: Update `SCHEMA` and add `_migrate`, call it from `connect`**

In `src/whachadoin/db.py`, replace the `log` block inside `SCHEMA` so it reads:

```python
CREATE TABLE IF NOT EXISTS log (
  id      INTEGER PRIMARY KEY,
  ts      TEXT NOT NULL,
  text    TEXT NOT NULL,
  todo_id INTEGER REFERENCES todos(id),
  path    TEXT NOT NULL DEFAULT '',
  repo    TEXT
);
```

Add this function above `connect`:

```python
def _migrate(conn: sqlite3.Connection) -> None:
    """Add path/repo columns to a pre-existing log table if absent. Idempotent."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(log)")}
    if "path" not in cols:
        conn.execute("ALTER TABLE log ADD COLUMN path TEXT NOT NULL DEFAULT ''")
    if "repo" not in cols:
        conn.execute("ALTER TABLE log ADD COLUMN repo TEXT")
    conn.commit()
```

In `connect`, add the `_migrate(conn)` call after the schema runs:

```python
def connect(db_path: str | os.PathLike | None = None) -> sqlite3.Connection:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS (all tests, including the whole pre-existing suite).

- [ ] **Step 5: Commit**

```bash
git add src/whachadoin/db.py tests/test_db.py
git commit -m "feat: add path/repo log columns with idempotent migration"
```

---

## Task 4: Auto-capture path + repo in `add_log` and `done_todo`

Make `add_log` resolve `path`/`repo` from the current process when not passed, persist them, and return them on the model. Route `done_todo`'s linked-log insert through `add_log` so completing a todo captures the same context.

**Files:**
- Modify: `src/whachadoin/db.py`
- Test: `tests/test_db.py` (append)

**Interfaces:**
- Consumes: `find_repo` (Task 2); the migrated `log` columns (Task 3); `LogEntry` (Task 1).
- Produces:
  - `add_log(conn, text: str, *, todo_id: int | None = None, path: str | None = None, repo: str | None = None) -> LogEntry` — `todo_id` is now keyword-only; when `path`/`repo` are `None`, resolves `path = os.getcwd()` and `repo = find_repo()`; INSERTs and returns a `LogEntry` with `path`/`repo` populated. Still raises `ValueError` on empty text.
  - `done_todo(conn, todo_id: int) -> Todo` — unchanged signature; its linked-log write now goes through `add_log(...)`, so path/repo are captured where `done` ran.

**Note:** No existing caller passes `todo_id` positionally (`cli.py` and `tui.py` call `add_log(conn, text)`; `done_todo` did a raw INSERT), so making `todo_id` keyword-only is safe. `# ponytail: keyword-only guards against silently swapping path into the todo_id slot.`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_db.py`:

```python
def test_add_log_auto_captures_path_and_repo(conn, tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    e = dbmod.add_log(conn, "did work here")
    assert e.path == str(tmp_path.resolve())
    assert e.repo == tmp_path.name
    # persisted, not just on the returned object
    row = dbmod.list_log(conn)[0]
    assert row.path == str(tmp_path.resolve())
    assert row.repo == tmp_path.name


def test_add_log_no_repo_outside_git(conn, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    e = dbmod.add_log(conn, "no repo here")
    assert e.path == str(tmp_path.resolve())
    assert e.repo is None


def test_add_log_explicit_path_repo_win(conn):
    e = dbmod.add_log(conn, "x", path="/explicit", repo="myrepo")
    assert e.path == "/explicit"
    assert e.repo == "myrepo"


def test_done_todo_log_captures_context(conn, tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    t = dbmod.add_todo(conn, "finish it")
    dbmod.done_todo(conn, t.id)
    entry = dbmod.list_log(conn)[0]
    assert entry.todo_id == t.id
    assert entry.repo == tmp_path.name
    assert entry.path == str(tmp_path.resolve())
```

`os.getcwd()` returns the real (symlink-resolved) path on macOS `tmp_path`, matching `tmp_path.resolve()`; `find_repo` also resolves, so the assertions line up.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_db.py -k "auto_captures or no_repo or explicit_path or done_todo_log" -v`
Expected: FAIL — `add_log` does not accept `path`/`repo` and does not populate them.

- [ ] **Step 3: Implement auto-capture**

In `src/whachadoin/db.py`, replace `add_log` with:

```python
def add_log(
    conn: sqlite3.Connection,
    text: str,
    *,
    todo_id: int | None = None,
    path: str | None = None,
    repo: str | None = None,
) -> LogEntry:
    text = text.strip()
    if not text:
        raise ValueError("log text must not be empty")
    if path is None:
        path = os.getcwd()
    if repo is None:
        repo = find_repo()
    entry = LogEntry(ts=_now(), text=text, todo_id=todo_id, path=path, repo=repo)
    cur = conn.execute(
        "INSERT INTO log (ts, text, todo_id, path, repo) VALUES (?, ?, ?, ?, ?)",
        (entry.ts, entry.text, entry.todo_id, entry.path, entry.repo),
    )
    conn.commit()
    entry.id = cur.lastrowid
    return entry
```

Then replace the linked-log INSERT inside `done_todo` (the `conn.execute("INSERT INTO log ...")` call) so `done_todo` reads:

```python
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
    add_log(conn, f"completed todo #{todo_id}: {todo.text}", todo_id=todo_id)
    conn.commit()
    return get_todo(conn, todo_id)
```

`add_log` auto-captures path/repo from the cwd where `done` ran, so the raw INSERT (and its `now` timestamp for the log row) is replaced. `# ponytail: reuse add_log so capture logic lives in one place.`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS (all tests; the pre-existing `test_done_todo_links_log_entry` still passes because the log row still carries `todo_id`).

- [ ] **Step 5: Commit**

```bash
git add src/whachadoin/db.py tests/test_db.py
git commit -m "feat: auto-capture path/repo in add_log and done_todo"
```

---

## Task 5: `kwd log ls` prints repo when present

Show the repo as a `[name]` tag on listing output, only when the entry has one. No new flags. No automated CLI test (matches the established convention — the CLI is verified by invocation).

**Files:**
- Modify: `src/whachadoin/cli.py`

**Interfaces:**
- Consumes: `LogEntry.repo` (Task 1); `db.list_log` (unchanged).
- Produces: no signature change; `log ls` output gains a `[repo] ` prefix on entries whose `repo` is set.

- [ ] **Step 1: Update the listing loop**

In `src/whachadoin/cli.py`, inside the `log` command's `if words and words[0] == "ls":` branch, replace the print loop with:

```python
    if words and words[0] == "ls":
        for e in dbmod.list_log(conn, today=today, since=since):
            link = f" (todo #{e.todo_id})" if e.todo_id else ""
            repo = f"[{e.repo}]  " if e.repo else ""
            typer.echo(f"{e.ts}  {repo}{e.text}{link}")
        return
```

- [ ] **Step 2: Verify end-to-end against a temp DB, inside and outside a git repo**

```bash
cd /home/user/projects/whachadoin
export WHACHADOIN_DB="$(mktemp -d)/log.db"
uv run kwd log "built the plugin"          # cwd IS a git repo → repo=whachadoin
cd "$(mktemp -d)"
uv run kwd log "one-off note, no repo"      # not a repo → no tag
uv run kwd --db "$WHACHADOIN_DB" log ls
cd /home/user/projects/whachadoin
unset WHACHADOIN_DB
```

Expected: the first entry lists as `…  [whachadoin]  built the plugin`; the second lists with no `[...]` tag. (Note the second `kwd log` writes to the *default* DB since `WHACHADOIN_DB` is unset by the subshell `cd`; pass `--db` explicitly, or run both writes with `--db "$WHACHADOIN_DB"`, if you want them in one file. The load-bearing check is the presence/absence of the `[repo]` tag.)

- [ ] **Step 3: Full suite green**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/whachadoin/cli.py
git commit -m "feat: show repo tag in kwd log ls output"
```

---

# PART 2 — the Claude Code plugin

> Part 2 is markdown/JSON config only — no unit tests. It depends on Part 1's auto-capture being merged. Formats below match real installed plugins under `~/.claude/plugins/cache/` (verified: string `source`, `.claude-plugin/` manifest location, SKILL/command frontmatter).

## Task 6: Marketplace + plugin manifests + README

Make the repo an installable marketplace pointing at a `plugin/` subdir, add the plugin manifest, and document the two setup prerequisites in the plugin README.

**Files:**
- Create: `.claude-plugin/marketplace.json`
- Create: `plugin/.claude-plugin/plugin.json`
- Create: `plugin/README.md`

**Interfaces:**
- Produces: a marketplace named `whachadoin` exposing one plugin (`whachadoin`, `"source": "./plugin"`); a plugin manifest that auto-discovers `plugin/skills/` and `plugin/commands/`.

- [ ] **Step 1: Create the marketplace manifest**

Create `.claude-plugin/marketplace.json`:

```json
{
  "name": "whachadoin",
  "owner": {
    "name": "Kerry Hatcher"
  },
  "plugins": [
    {
      "name": "whachadoin",
      "description": "Cross-session work logging: drive the kwd CLI to log work, manage persistent todos, and recall what you worked on.",
      "source": "./plugin",
      "version": "0.1.0"
    }
  ]
}
```

- [ ] **Step 2: Create the plugin manifest**

Create `plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "whachadoin",
  "description": "Log work, manage persistent cross-session todos, and answer \"what am I working on\" / \"what did I work on last week\" by driving the kwd CLI.",
  "version": "0.1.0",
  "author": {
    "name": "Kerry Hatcher"
  },
  "keywords": [
    "worklog",
    "todo",
    "productivity",
    "kwd"
  ]
}
```

`skills/` and `commands/` under the plugin root are auto-discovered — no need to enumerate them here (matches the superpowers manifest, which lists neither).

- [ ] **Step 3: Create the plugin README with setup prerequisites**

Create `plugin/README.md`:

```markdown
# whachadoin plugin

Drives the `kwd` work-log CLI from any Claude Code session: log work, manage
persistent todos, and recall what you worked on. Path and git repo are captured
automatically on every log entry.

## Prerequisites (one-time)

1. **Install the `kwd` CLI globally (editable):**

   ```bash
   uv tool install --editable ~/projects/whachadoin
   ```

   Editable means core edits apply without reinstalling.

2. **Add this repo as a plugin marketplace and install the plugin:**

   ```
   /plugin marketplace add ~/projects/whachadoin
   ```

   Then install the `whachadoin` plugin from that marketplace via `/plugin`.

If `kwd` is not found later, re-run step 1.

## What you get

- **Skill `worklog`** — auto-invoked on phrases like "log this", "add a todo",
  "what am I working on", "what did I work on last week".
- **`/log <text>`** — record a work-log entry (path + repo captured automatically).
- **`/worklog [since]`** — summarize recent log entries and open todos.

Persistent `kwd` todos are separate from Claude Code's in-session task list; the
skill only writes to `kwd` when you explicitly want something remembered.
```

- [ ] **Step 4: Validate the JSON parses**

```bash
cd /home/user/projects/whachadoin
uv run python -c "import json; json.load(open('.claude-plugin/marketplace.json')); json.load(open('plugin/.claude-plugin/plugin.json')); print('json ok')"
```

Expected: prints `json ok`.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/marketplace.json plugin/.claude-plugin/plugin.json plugin/README.md
git commit -m "feat: add whachadoin marketplace, plugin manifest, and README"
```

---

## Task 7: `worklog` skill

Author the trigger-phrase skill. Its `description` carries the phrases that make Claude auto-invoke it; its body instructs Claude how to drive `kwd`, with the explicit guardrail separating persistent `kwd` todos from the in-session task list.

**Files:**
- Create: `plugin/skills/worklog/SKILL.md`

**Interfaces:**
- Consumes: the `kwd` CLI (`kwd log`, `kwd log ls --since`, `kwd todo add/done/ls`) — path/repo auto-captured by Part 1.
- Produces: a skill named `worklog` discoverable by the plugin.

- [ ] **Step 1: Write the skill**

Create `plugin/skills/worklog/SKILL.md`:

```markdown
---
name: worklog
description: |
  Log work and manage persistent, cross-session todos via the `kwd` CLI, and recall past work. Use this skill whenever the user says "log this", "log that", "add a todo", "add to my list", "remind me to", "what am I working on", "what did I work on" (last week / yesterday / since a date), or otherwise wants to record or recall work that should persist beyond the current session. Path and git repo are captured automatically by `kwd`.
allowed-tools:
  - Bash(kwd *)
---

# worklog

Drive the `kwd` CLI to record and recall work. All entries persist in one shared
SQLite store across every Claude Code session.

## Guardrail: two separate todo systems

`kwd` todos are **persistent and cross-session**. Claude Code's built-in
in-session TodoWrite / Task planning list is **ephemeral**. Keep them separate:

- Use `kwd todo add` ONLY when the user explicitly wants something remembered
  beyond this session ("add a todo to my list", "track this for later",
  "remind me to ...").
- Do NOT route your in-session planning list through `kwd`, and do NOT mirror
  ephemeral planning items into `kwd`.

## Logging work

Run:

```bash
kwd log "<concise one-line summary of what was done>"
```

Path and git repo are captured automatically by `kwd` — do **not** prefix the
repo name into the text. On "log this", first summarize the relevant recent work
in one line, then log that line.

## Todos

```bash
kwd todo add "<text>" [--priority N]   # add a persistent todo
kwd todo done <id>                      # complete one (records a linked log entry)
kwd todo ls                             # list open todos
```

## "What am I working on?"

Run `kwd todo ls` and recent `kwd log ls`, then summarize. Group by repo when it
makes the picture clearer.

## "What did I work on last week / since X?"

Today's date is known to you. Compute the start date and run:

```bash
kwd log ls --since YYYY-MM-DD
```

Group the returned entries by the `[repo]` tag in the output and summarize per
repo.

## If `kwd` is missing

If a `kwd` command fails with "command not found", tell the user to install it:
`uv tool install --editable ~/projects/whachadoin` (see the plugin README).
```

- [ ] **Step 2: Validate the frontmatter parses**

```bash
cd /home/user/projects/whachadoin
uv run python -c "import re,sys; t=open('plugin/skills/worklog/SKILL.md').read(); assert t.startswith('---'); print('frontmatter present:', '---' in t[3:])"
```

Expected: prints `frontmatter present: True`.

- [ ] **Step 3: Commit**

```bash
git add plugin/skills/worklog/SKILL.md
git commit -m "feat: add worklog trigger-phrase skill"
```

---

## Task 8: `/log` and `/worklog` commands

Add the two slash commands. `/log` records an entry; `/worklog` summarizes recent log + open todos. No `/todo` command (YAGNI — todo management goes through the skill via natural language).

**Files:**
- Create: `plugin/commands/log.md`
- Create: `plugin/commands/worklog.md`

**Interfaces:**
- Consumes: `kwd log`, `kwd log ls`, `kwd todo ls`.
- Produces: slash commands `/log` and `/worklog` under the `whachadoin` plugin.

- [ ] **Step 1: Create `/log`**

Create `plugin/commands/log.md`:

```markdown
---
description: "Record a work-log entry (path + repo captured automatically)"
argument-hint: "<text>"
allowed-tools: ["Bash(kwd *)"]
---

Record a work-log entry with the `kwd` CLI. The current directory and git repo
are captured automatically — do not prefix the repo into the text.

Run:

```bash
kwd log "$ARGUMENTS"
```

Then confirm to the user what was logged. If `$ARGUMENTS` is empty, ask the user
what to log instead of running the command.
```

- [ ] **Step 2: Create `/worklog`**

Create `plugin/commands/worklog.md`:

```markdown
---
description: "Summarize recent work-log entries and open todos"
argument-hint: "[since]"
allowed-tools: ["Bash(kwd *)"]
---

Summarize recent work and outstanding todos.

If `$ARGUMENTS` is a date (`YYYY-MM-DD`) or a phrase you can resolve to one
(today's date is known to you), pass it as `--since`:

```bash
kwd log ls --since <resolved-date>
```

Otherwise list recent entries:

```bash
kwd log ls
```

Then always list open todos:

```bash
kwd todo ls
```

Summarize the results for the user, grouping log entries by the `[repo]` tag in
the output when it makes the picture clearer.
```

- [ ] **Step 3: Commit**

```bash
git add plugin/commands/log.md plugin/commands/worklog.md
git commit -m "feat: add /log and /worklog plugin commands"
```

---

## Task 9: Manual smoke check (verification)

The plugin has no unit tests. This documented manual check confirms the whole path works end-to-end: install `kwd`, add the marketplace, and verify repo capture inside and outside a git repo.

**Files:** none (verification only).

- [ ] **Step 1: Install the CLI and marketplace**

```bash
uv tool install --editable ~/projects/whachadoin
```

In Claude Code: `/plugin marketplace add ~/projects/whachadoin`, then install the `whachadoin` plugin via `/plugin`.

- [ ] **Step 2: Log inside a git repo and confirm the repo is captured**

```bash
cd ~/projects/whachadoin
kwd log "smoke test inside repo"
kwd log ls
```

Expected: the entry lists with a `[whachadoin]` tag. (Equivalently, run `/log smoke test inside repo` from a Claude Code session whose cwd is the repo.)

- [ ] **Step 3: Log outside any git repo and confirm the repo is blank**

```bash
cd "$(mktemp -d)"
kwd log "smoke test outside repo"
kwd log ls
```

Expected: the newest entry lists with **no** `[...]` tag.

- [ ] **Step 4: Confirm the skill triggers (optional, interactive)**

In a Claude Code session with the plugin installed, say "what did I work on last
week" and confirm Claude invokes the `worklog` skill and runs
`kwd log ls --since <date>`.

- [ ] **Step 5: Record completion**

No commit required (nothing changed). Note the smoke check passed in the PR / handoff.

---

## Self-Review

**Spec coverage:**
- `log` gains `path TEXT NOT NULL DEFAULT ''` + `repo TEXT` — Task 3 (`SCHEMA` + `_migrate`). ✅
- Pure-Python `find_repo()` walk-up, `.git` file-or-dir, no subprocess — Task 2. ✅
- `add_log` auto-resolves path/repo when omitted — Task 4. ✅
- `done_todo` linked log captures the same — Task 4. ✅
- `LogEntry` gains `path: str`, `repo: Optional[str]` — Task 1. ✅
- Idempotent migration via `PRAGMA table_info` + `ALTER TABLE` — Task 3. ✅
- `kwd log ls` prints repo when present — Task 5. ✅
- Part 1 tests: find_repo cases, add_log auto-capture via monkeypatch.chdir, migration on old-shape DB, LogEntry round trip — Tasks 1–4. ✅
- Marketplace at repo root, one plugin `"source": "./plugin"` — Task 6. ✅
- `plugin/.claude-plugin/plugin.json`, `skills/worklog/SKILL.md`, `commands/log.md`, `commands/worklog.md`, `README.md` — Tasks 6–8. ✅
- No hooks — none added. ✅
- SKILL description carries trigger phrases; instructs the two-todo-systems guardrail, `kwd log` without repo prefix, todo add/done, "what am I working on" via todo ls + log ls, "what did I work on last week" via `--since` grouped by repo, and the install fallback — Task 7. ✅
- Commands `/log` and `/worklog` only (no `/todo`) — Task 8. ✅
- Setup prereqs (`uv tool install --editable`, `/plugin marketplace add`) documented — Task 6 README + Task 9. ✅
- Part 2 testing = one documented manual smoke check (repo capture inside git, blank outside) — Task 9. ✅
- Build order Part 1 → Part 2 — enforced by task order and the Part 2 header note. ✅
- Out-of-scope items (todos path/repo, `--repo` filter, hooks, session-start injection, `/todo`) — not implemented. ✅

**Placeholder scan:** No TBD/TODO/"add error handling" placeholders; every code and config step shows complete content.

**Type consistency:** `find_repo(start=None) -> str | None`, `add_log(conn, text, *, todo_id=None, path=None, repo=None) -> LogEntry`, `_migrate(conn) -> None`, and `LogEntry(... path: str = "", repo: Optional[str] = None)` are used identically across the db.py implementation (Tasks 2–4), the CLI consumer (Task 5), and the Interfaces blocks. SQL column names `path`/`repo` match the model field names used in `LogEntry(**dict(row))`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-09-worklog-plugin.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.
