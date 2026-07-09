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
