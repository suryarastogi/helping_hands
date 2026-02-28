# Project todos

The canonical checklist lives in the repo root: **`TODO.md`**. This note is for design notes or decisions that affect the todos.

## Summary (from TODO.md)

1. **Set up Python project** — done (layout, tooling, CI/CD, tests)
2. **Dockerise app mode and add Compose** — done (server, workers, beat, redis, postgres, flower)
3. **Autodocs generation** — done (MkDocs Material + mkdocstrings, CI deploy to GitHub Pages)
4. **Hand backend scaffolding vs implementation** — all CLI backends implemented (`codexcli`, `claudecodecli`, `goose`, `geminicli`); E2E hardening still pending
5. **Skills system** — done (execution, web, prd, ralph)
6. **Scheduled tasks** — done (RedBeat + croniter, `/schedules` API, app UI)

## Design notes

- E2E PR updates are now treated as **state refresh**: live runs update both PR body and marker comment with latest timestamp/commit/prompt.
- CI integration policy: only `master` + Python `3.13` performs live push/update; other matrix jobs force dry-run to avoid PR branch race conditions.
- Pre-commit now includes `ty` for type checks; current rule ignores are intentional until optional backend imports/protocol signatures are tightened.
- Basic iterative backends now default to a final commit/push/PR step; explicit `--no-pr` disables side effects (and maps to dry-run for E2E).
- Non-E2E CLI supports `owner/repo` input by cloning to temporary workspace before indexing/iteration.
- Hand internals were split from a single `hand.py` into a package module (`lib/hands/v1/hand/`); shared filesystem system tools now live in `lib/meta/tools/filesystem.py` and are also exposed via MCP filesystem tools.
- Provider routing is now centralized in `lib/ai_providers/` plus `lib/hands/v1/hand/model_provider.py`, replacing direct provider client construction in hands.
- Basic iterative hands now preload iteration-1 context from `README.md`, `AGENT.md`, and a bounded file-tree snapshot.
- CI and local test runs now include coverage reporting (`pytest-cov`), and README shows a Codecov badge.
- App-mode monitoring now supports both JS polling (`/tasks/{task_id}`) and a no-JS fallback monitor (`/monitor/{task_id}` with auto-refresh), reducing browser-dependent failures.
- Monitor UI now uses fixed-size task/status/update/payload cells with in-cell scrolling to keep layout stable during polling.
- `claudecodecli` now includes a one-time no-change enforcement pass for edit-intent prompts and defaults to non-interactive permissions skip (configurable), reducing "prose-only/no-edit" runs.
- `claudecodecli` command resolution now includes fallback to `npx -y @anthropic-ai/claude-code` when `claude` binary is unavailable; docs now call out that fallback requires network access in worker runtimes.
- Compose file is `compose.yaml` (not `docker-compose.yml`) and now sets default in-network Redis/Celery URLs for server/worker/beat/flower/mcp services when `.env` is sparse.
- All four CLI backends (`codexcli`, `claudecodecli`, `goose`, `geminicli`) are now fully implemented with two-phase flows, subprocess streaming, heartbeats, and idle timeout.
- `goose` backend auto-derives `GOOSE_PROVIDER`/`GOOSE_MODEL` from model config, injects `--with-builtin developer`, and mirrors GH_TOKEN for subprocess auth.
- `geminicli` backend injects `--approval-mode auto_edit` by default and retries without `--model` on model unavailability.
- Dynamic skill registry (`lib/meta/skills/`) provides composable tool bundles; `enable_execution`/`enable_web` flags fold into skills automatically.
- Cron-scheduled build tasks implemented via RedBeat + croniter (`server/schedules.py`); `/schedules` REST API + built-in UI for CRUD/trigger/presets.
- System tools expanded: `lib/meta/tools/command.py` (Python/Bash execution) and `lib/meta/tools/web.py` (search/browse) alongside `filesystem.py`.
