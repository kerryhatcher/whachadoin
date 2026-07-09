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
