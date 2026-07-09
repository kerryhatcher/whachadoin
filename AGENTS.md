# Agent instructions — whachadoin

Work log + todo tracker (`kwd` CLI/TUI) plus a Claude Code plugin that drives it from
any session. See `docs/superpowers/specs/` and `docs/superpowers/plans/` for designs.

## Publishing the plugin to the marketplace

The plugin is listed on the personal marketplace repo
**https://github.com/kerryhatcher/hatch-plugins**. That marketplace references this repo;
it does not hold a copy. So whenever the plugin changes in a way the marketplace should
pick up, the marketplace needs to be told.

**After the plugin is updated and merged to `main`:**

1. Bump the `version` in `plugin/.claude-plugin/plugin.json`.
2. Merge to `main`.
3. An issue is opened automatically on `kerryhatcher/hatch-plugins` by the
   `.github/workflows/marketplace-issue.yml` workflow (fires when the plugin manifest's
   version changes on `main`). Nothing else to do if the workflow is enabled and its
   token secret is set.

**If the workflow is disabled or its token is missing, open the issue manually:**

```bash
# NOTE: this machine's gh is usually authed to Cox GHE, not github.com.
# Auth to github.com first (one time):  gh auth login -h github.com
gh issue create -R kerryhatcher/hatch-plugins \
  --title "Add/update whachadoin plugin vX.Y.Z" \
  --body "Please add/update the **whachadoin** plugin in the marketplace.

- Source repo: https://github.com/kerryhatcher/whachadoin
- Plugin path: ./plugin  (manifest: plugin/.claude-plugin/plugin.json)
- Version: vX.Y.Z
- Adds cross-session work logging + todo tracking via the kwd CLI."
```

Replace `vX.Y.Z` with the value from `plugin/.claude-plugin/plugin.json`.

## The Action's token

The workflow needs a token that can create issues in `kerryhatcher/hatch-plugins` — the
default `GITHUB_TOKEN` cannot write to another repo. Create a fine-grained PAT with
**Issues: write** on `hatch-plugins`, and store it in this repo's secrets as
`HATCH_PLUGINS_TOKEN` (Settings → Secrets and variables → Actions). Until that secret
exists the workflow no-ops with a log message instead of failing.

## Build / test conventions

- uv-managed, Python 3.13. **Always `uv run ...`** — a hook blocks bare `python`/`pytest`.
- Add deps via `uv add` / `uv add --dev`. Tests: `uv run pytest`.
