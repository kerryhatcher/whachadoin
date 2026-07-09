# whachadoin — cross-session work logging plugin

Make the `kwd` work log usable from **any** Claude Code session so that "log this",
"add a todo", "what am I working on", and "what did I work on last week" all route to
one shared SQLite store. Two parts: a small change to whachadoin core (capture path +
repo on every log entry) and a Claude Code plugin (skill + commands) that drives `kwd`.

## Part 1 — whachadoin core: path + repo columns on `log`

### Schema

`log` gains two columns:

```sql
log(
  id      INTEGER PRIMARY KEY,
  ts      TEXT NOT NULL,               -- ISO-8601 UTC
  text    TEXT NOT NULL,
  todo_id INTEGER REFERENCES todos(id),
  path    TEXT NOT NULL DEFAULT '',    -- cwd where kwd ran
  repo    TEXT                          -- git repo name, or NULL
)
```

- `path` = the working directory the `kwd` command ran in (`os.getcwd()`).
- `repo` = name of the git repo the cwd belongs to, else NULL.

### Repo detection

Pure-Python walk-up, no `git` subprocess (works in worktrees where `.git` is a file):

1. Start at cwd.
2. If `<dir>/.git` exists (file or directory), `repo` = `basename(dir)`; stop.
3. Else ascend to parent. Stop at filesystem root.
4. No `.git` found anywhere in the chain → `repo = None`.

Helper `find_repo(start: str | None = None) -> str | None` in `db.py` (or a small
`context.py`). `path` capture is `os.getcwd()`.

### Migration (idempotent)

Existing DBs already have a `log` table without these columns. On connection/schema init:

1. `CREATE TABLE IF NOT EXISTS log (... with path/repo ...)` for fresh DBs.
2. For existing DBs, read `PRAGMA table_info(log)`; if `path` or `repo` is missing,
   `ALTER TABLE log ADD COLUMN path TEXT NOT NULL DEFAULT ''` / `ADD COLUMN repo TEXT`.
   (`ALTER TABLE ADD COLUMN` with a constant default is valid in SQLite; existing rows
   backfill `path=''`, `repo=NULL`.)

Runs every connection open; safe to repeat.

### Model + CRUD

- `LogEntry` Pydantic model gains `path: str` and `repo: Optional[str]`.
- `add_log(conn, text, *, todo_id=None, path=None, repo=None)`: when `path`/`repo` are
  omitted, resolve them from the current process (`os.getcwd()` + `find_repo()`), so both
  the CLI and the internal call inside `done_todo` capture context automatically.
- `done_todo`'s linked-log insert captures the same path/repo (where `done` ran).

### CLI display

`kwd log ls` prints repo when present, e.g.:

```
2026-07-09T14:03:22Z  [whachadoin]  built the TUI
2026-07-09T13:10:01Z                one-off note with no repo
```

No new flags required. (A `--repo` filter is out of scope; YAGNI.)

### Tests (added to existing suite, all `uv run`)

- `find_repo`: cwd with `.git` → name; nested subdir → nearest ancestor repo name;
  no `.git` in chain → None. Use `tmp_path` with a fake `.git`.
- `add_log` auto-captures path (== a controlled cwd via `monkeypatch.chdir`) and repo.
- Migration: create a DB with an old-shape `log` table, open via the app, confirm the
  columns get added and existing rows read back with `path=''`, `repo=None`.
- `LogEntry` round trip with path/repo populated.

## Part 2 — the Claude Code plugin

### Prerequisites (documented in the plugin README/skill)

1. `uv tool install --editable ~/projects/whachadoin` → `kwd` on PATH globally
   (editable, so core edits apply without reinstall).
2. `/plugin marketplace add ~/projects/whachadoin` then install the `whachadoin` plugin.

### Repo layout added

```
.claude-plugin/marketplace.json      # repo is an installable marketplace
plugin/
  .claude-plugin/plugin.json         # plugin manifest
  skills/worklog/SKILL.md            # trigger-phrase skill
  commands/log.md                    # /log <text>
  commands/worklog.md                # /worklog [since]
  README.md                          # setup steps
```

`marketplace.json` lists one plugin with `"source": "./plugin"`.

**No hooks.** Nothing fires automatically; all capture is user-triggered.

### Skill: `worklog`

Description carries the trigger phrases so Claude auto-invokes it: *"log this",
"log that", "add a todo", "add to my list", "remind me to", "what am I working on",
"what did I work on" (last week / yesterday / since ...)*.

Skill instructions tell Claude:

- **Two todo systems, kept separate.** `kwd` todos are persistent and cross-session —
  use them ONLY when the user explicitly wants something remembered beyond the session
  ("add a todo to my list", "track this for later"). Do NOT route Claude Code's built-in
  in-session TodoWrite/Task planning list through `kwd`, and do not mirror ephemeral
  planning items into `kwd`. Explicit guardrail.
- **Log work:** run `kwd log "<concise summary of what was done>"`. Path + repo are
  captured automatically by `kwd` (Part 1) — do NOT prefix the repo into the text.
  On "log this", summarize the relevant recent work in one line before logging.
- **Add / complete todos:** `kwd todo add "<text>" [--priority N]`, `kwd todo done <id>`.
- **"What am I working on"** → run `kwd todo ls` and recent `kwd log ls`; summarize,
  grouping by repo when useful.
- **"What did I work on last week / since X"** → compute the date (today is known),
  run `kwd log ls --since YYYY-MM-DD`, group entries by the `repo` column, summarize.
- If `kwd` is missing (command not found), tell the user to run the install step.

### Commands

- `/log <text>` → `kwd log "<text>"` (context auto-captured).
- `/worklog [since]` → `kwd log ls [--since <since>]` + `kwd todo ls`, then summarize.

Todo management is left to natural language via the skill (no `/todo` command — YAGNI).

### Testing

Plugin is markdown/config — no unit tests. One manual smoke check documented in the
plan: install kwd, run `/log test entry` (or `kwd log "test"`) inside a git repo,
confirm `kwd log ls` shows the entry with the right repo, and inside a non-repo dir
confirm repo is blank.

## Build order

1. Part 1 (core schema/model/cli/tests) — the columns must exist first.
2. Part 2 (plugin) — depends on the auto-capture behavior from Part 1.

## Out of scope (YAGNI)

- path/repo columns on `todos` (spec covers `log` only).
- `--repo` filter on `kwd log ls`.
- Automatic logging via hooks (session-end summaries, markers).
- Session-start context injection.
