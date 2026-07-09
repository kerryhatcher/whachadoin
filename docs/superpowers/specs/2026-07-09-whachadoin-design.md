# whachadoin — work log + todo CLI/TUI

Personal work journal and todo tracker. CLI for quick capture, TUI for browsing.

## Stack

- Python 3.13, uv-managed
- Deps: `typer` (CLI), `pydantic` (validation), `textual` (TUI)
- Storage: SQLite via stdlib `sqlite3` (no ORM; Pydantic models validate rows in/out)

## Layout

```
src/whachadoin/
  __init__.py
  models.py   # Pydantic: Todo, LogEntry
  db.py       # connection, schema init, CRUD
  cli.py      # Typer app (console entry: kwd)
  tui.py      # Textual app (kwd tui)
tests/
  test_db.py
```

`pyproject.toml` → `[project.scripts]` `kwd = "whachadoin.cli:app"`.

## Data model (linked)

Two tables, one DB.

```sql
todos(
  id         INTEGER PRIMARY KEY,
  text       TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'open',   -- 'open' | 'done'
  priority   INTEGER NOT NULL DEFAULT 0,      -- higher = more urgent
  created_at TEXT NOT NULL,                   -- ISO 8601
  done_at    TEXT                             -- ISO 8601, NULL until done
)

log(
  id      INTEGER PRIMARY KEY,
  ts      TEXT NOT NULL,                       -- ISO 8601
  text    TEXT NOT NULL,
  todo_id INTEGER REFERENCES todos(id)         -- NULL = freestanding entry
)
```

**Link:** marking a todo done sets `status='done'`, `done_at=now`, and inserts a `log` row referencing that todo. This is the only cross-table write.

Pydantic models mirror rows:
- `Todo`: id (Optional on insert), text, status (Literal), priority, created_at, done_at (Optional)
- `LogEntry`: id (Optional), ts, text, todo_id (Optional)

Status is a `Literal["open","done"]`; validation lives in the model, not the DB.

## DB location

Resolve in this order:
1. `$XDG_DATA_HOME` set → `$XDG_DATA_HOME/whachadoin/log.db`
2. else → `~/.whachadoin/log.db`

Tiny helper in `db.py`; no `platformdirs` dependency. Create parent dir on first use. `--db PATH` flag / `WHACHADOIN_DB` env var override for tests and power use.

## CLI (`kwd`)

| command | behavior |
|---|---|
| `kwd log "text"` | insert freestanding log entry |
| `kwd todo add "text" [--priority N]` | insert open todo |
| `kwd todo done <id>` | mark done + auto-insert linked log entry |
| `kwd todo ls [--all]` | list open todos (—all includes done), sorted by priority desc then created_at |
| `kwd log ls [--today] [--since YYYY-MM-DD]` | list log entries newest-first; filters narrow the window |
| `kwd tui` | launch Textual UI |

Output: plain text tables (Typer/rich built-in). Errors (bad id, empty text) exit non-zero with a one-line message.

## TUI

Textual app, single screen:
- Left pane: todos list (open by default), selectable.
- Right pane: log feed, newest first.
- Footer input box.

Keybinds: `a` add todo, `l` add log entry, `d` mark selected todo done, `r` refresh, `q` quit. Adds/dones write through the same `db.py` functions the CLI uses, then refresh both panes.

## Error handling

- All timestamps ISO 8601, UTC, generated in `db.py`.
- `db.py` functions raise on missing id / empty text; CLI catches and prints a clean message + non-zero exit.
- Schema init is idempotent (`CREATE TABLE IF NOT EXISTS`), run on every connection open.

## Testing

pytest, in-memory / temp-file SQLite via the `--db` override:
- CRUD round trips (add todo, list, done → status+done_at+linked log row present).
- Pydantic validation (bad status rejected).
- DB path resolution (XDG set vs unset).

No TUI tests (manual); no CLI-invocation tests beyond what db coverage gives.

## Out of scope (YAGNI)

Tags, full-text search, edit/delete, recurring todos, multi-user, sync, config file. Add when a real need appears.
