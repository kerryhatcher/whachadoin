---
name: worklog
description: Log work and track persistent todos with kwd. Trigger phrases — "log this", "log that", "add a todo", "add to my list", "remind me to", "what am I working on", "what did I work on" (last week / yesterday / since ...).
allowed-tools:
  - Bash(kwd *)
---

# worklog

Drives the `kwd` CLI (whachadoin) for cross-session work logging and todos.

## Guardrail: two separate todo systems

Claude Code's built-in in-session `TodoWrite`/Task planning list is **ephemeral**
and scoped to the current session. `kwd` todos are **persistent** and cross-session.

- Do NOT mirror ephemeral planning-list items into `kwd`.
- Only use `kwd todo add` when the user explicitly wants something remembered
  beyond this session (e.g. "add a todo to my list", "remind me to X", "track
  this for later").
- Never treat "log this" as a cue to also add a `kwd` todo, and never treat
  in-session task planning as a cue to log or add a todo — they are unrelated.

## Log work

```
kwd log "<concise summary of what was done>"
```

Path and repo are captured automatically by `kwd` — do NOT prefix the repo or
path into the text yourself. On "log this", summarize the relevant recent
work into one concise line before logging it.

## Proactive journaling (no prompt needed)

When you finish a **substantial** task or milestone — the kind where you'd
naturally write an end-of-task recap — also persist a 1-3 line high-level recap
with `kwd log "<recap>"`, without being asked. One entry per completed task, not
per step; high-level, not line-by-line; skip trivial exchanges and mid-task
progress. A SessionStart hook reminds you of this each session. Note briefly that
you logged it; don't narrate it heavily.

## Add / complete todos

```
kwd todo add "<text>" [--priority N]
kwd todo done <id>
```

## "What am I working on?"

Run `kwd todo ls` (open todos) and `kwd log ls` (recent entries), then
summarize the two together.

## "What did I work on last week / since X?"

Compute the requested date, then run:

```
kwd log ls --since YYYY-MM-DD
```

Group the results by the `repo` column shown in each entry and summarize
per-repo.

## If `kwd` is not found

Tell the user to run the install step from the plugin's README before
retrying.
