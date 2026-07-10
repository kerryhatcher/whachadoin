#!/usr/bin/env bash
# SessionStart hook: inject a short, always-on instruction so Claude proactively
# journals high-level recaps of substantial work via `kwd log`. Instruction only —
# no data (todos/history) is injected. Emitted as SessionStart additionalContext.
set -euo pipefail

cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Work journaling (whachadoin plugin): when you finish a SUBSTANTIAL task or milestone — the kind of work where you'd naturally write an end-of-task recap (a feature built, a bug fixed, an investigation concluded) — also persist a high-level recap to the cross-session work log with:\n  kwd log \"<1-3 line high-level recap>\"\nGuidance: one entry per completed task, NOT per step; keep it high-level, not line-by-line; skip trivial exchanges, single-file tweaks, and mid-task progress. Do it without being asked, but do not narrate it heavily — a brief note that you logged it is enough. This is the persistent journal and is separate from Claude Code's in-session todo/plan list; never mirror ephemeral planning items into it. If `kwd` is not installed, skip silently."}}
JSON
