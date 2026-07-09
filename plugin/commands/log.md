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
