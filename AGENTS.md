# Agent instructions — whachadoin

Work log + todo tracker (`kwd` CLI/TUI) plus a Claude Code plugin that drives it from
any session. See `docs/superpowers/specs/` and `docs/superpowers/plans/` for designs.

## Versioning & releases (release-please)

Versions and releases are automated by **release-please** — do NOT bump versions by hand.

- Commit with **Conventional Commits** (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`,
  `feat!:`/`BREAKING CHANGE:` for majors). release-please reads them.
- `.github/workflows/release-please.yml` maintains a standing **release PR** on `main`
  that bumps the version, updates `CHANGELOG.md`, and — when merged — tags and publishes
  a GitHub Release. Config: `release-please-config.json` + `.release-please-manifest.json`.
- Single repo-wide version (bumps `pyproject.toml`). **When the plugin is built**, add its
  manifest to the package's `extra-files` in `release-please-config.json` (see the
  `$comment` there) so `plugin/.claude-plugin/plugin.json` version tracks releases.

## Publishing the plugin to the marketplace

The plugin is listed on the personal marketplace repo
**https://github.com/kerryhatcher/hatch-plugins**. That marketplace references this repo;
it does not hold a copy. So each release, the marketplace is told to pick up the change.

**Flow:** merge the release-please PR → `release-please.yml` publishes a GitHub Release
AND, in the same run (its `Notify marketplace` step, gated on `release_created`), opens an
issue on `kerryhatcher/hatch-plugins`. Nothing manual if the token secret is set.

Why the notify step is inside `release-please.yml` and not a separate `on: release`
workflow: a release published by the default `GITHUB_TOKEN` does **not** trigger other
workflows (GitHub recursion guard), so an `on: release` trigger would silently never fire.

**If the workflow is disabled or its token is missing, open the issue manually:**

```bash
# NOTE: prefix GH_HOST=github.com (default host is Cox GHE). See the gh section below.
GH_HOST=github.com gh issue create -R kerryhatcher/hatch-plugins \
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

## GitHub CLI — host switching (IMPORTANT)

`gh`'s default host may not be **github.com** (e.g. if a GitHub Enterprise host is configured
as the default). This repo and the marketplace live on **github.com**. `-R owner/repo` does
NOT switch hosts — it resolves against the default, so a bare
`gh -R kerryhatcher/whachadoin ...` can hit the wrong host and 404.

**For any github.com repo, prefix `GH_HOST=github.com`:**

```bash
GH_HOST=github.com gh pr list  -R kerryhatcher/whachadoin
GH_HOST=github.com gh run list -R kerryhatcher/whachadoin
GH_HOST=github.com gh issue create -R kerryhatcher/hatch-plugins ...
```

Check both hosts are authenticated with `gh auth status`; if the correct account is already
active for each host, no `gh auth switch` is needed — only the host prefix.

One-time repo setting (already applied to whachadoin, redo for new repos) so release-please
can open its PR:

```bash
GH_HOST=github.com gh api -X PUT repos/<owner>/<repo>/actions/permissions/workflow \
  -F default_workflow_permissions=write -F can_approve_pull_request_reviews=true
```

## Build / test conventions

- uv-managed, Python 3.13. **Always `uv run ...`** — a hook blocks bare `python`/`pytest`.
- Add deps via `uv add` / `uv add --dev`. Tests: `uv run pytest`.
