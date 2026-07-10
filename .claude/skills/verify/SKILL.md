---
name: verify
description: Exercise the whachadoin kwd CLI end-to-end to verify a change works at its real surface.
---

# Verify whachadoin

Surface is the `kwd` CLI (a Typer app). Drive it, don't run pytest.

## Handle

Always use an isolated DB so you never touch the real `~/.whachadoin/log.db`:

```bash
cd ~/projects/whachadoin
export WHACHADOIN_DB="$(mktemp -d)/verify.db"
uv run kwd --help          # kwd is the project console script; ALWAYS `uv run` (hook blocks bare python)
```

Outside the project dir, invoke with `uv run --project ~/projects/whachadoin kwd ...`.

## Flows worth driving

```bash
uv run kwd todo add "task" --priority 5     # priority sorts desc in `todo ls`
uv run kwd todo ls [--all]                  # open only; --all includes done
uv run kwd log "did a thing"                # path+repo auto-captured (repo = nearest .git ancestor)
uv run kwd todo done <id>                   # marks done AND writes a linked log entry
uv run kwd log ls [--today] [--since YYYY-MM-DD]
```

Check: `todo done` writes exactly one linked `completed todo #N` log row and is
idempotent (running it twice must NOT add a second row). `log ls` shows `[repo]` when
inside a git tree, no tag outside one.

## Known sharp edges (not regressions)

- `log ls --since <malformed>` silently returns empty + exit 0 (lexicographic string
  compare on the ISO timestamp, no date validation). By design (ponytail note in db.py).
- `todo done` on an already-done id still prints `done: #N ...` (returns unchanged).
