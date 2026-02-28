# Project todos

The canonical checklist lives in the repo root: **`TODO.md`**. This note is for design notes or decisions that affect the todos.

## Summary (from TODO.md)

1. **Set up Python project** under `src/helping_hands` ✓ — Layout, tooling, CI/CD, tests all complete.

2. **Dockerise app mode and add Compose** ✓ — `compose.yaml` with server, workers, beat, Redis, Postgres, Flower.

3. **Autodocs generation and serving on GitHub** ✓ — MkDocs Material + mkdocstrings; CI builds and deploys to GitHub Pages.

4. **Hand backend scaffolding vs implementation** — All CLI backends now implemented (`codexcli`, `claudecodecli`, `goose`, `geminicli`). Full backend routing in CLI and app mode. Remaining: E2E hardening (branch collision, draft PR, idempotency).

5. **Skills and scheduling** ✓ — Dynamic skill registry (`execution`, `web`, `prd`, `ralph`) in `lib/meta/skills/`. Cron scheduling via RedBeat + Redis with `/schedules` CRUD and scheduled-tasks UI.

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
- `goose` backend auto-derives `GOOSE_PROVIDER`/`GOOSE_MODEL` from `HELPING_HANDS_MODEL` (default: `ollama`/`llama3.2:latest`), injects `--with-builtin developer`, and mirrors `GH_TOKEN`↔`GITHUB_TOKEN`.
- `geminicli` backend injects `--approval-mode auto_edit` for non-interactive runs and retries once without `--model` on deprecated-model rejection.
- Skills system (`lib/meta/skills/`) provides composable tool bundles (`execution`, `web`, `prd`, `ralph`) selected per run via `skills` field; legacy `enable_execution`/`enable_web` flags are automatically folded in.
- Cron scheduling via RedBeat + Redis (`server/schedules.py`); full CRUD on `/schedules` endpoints; Beat dispatches `scheduled_build` Celery tasks; UI has a scheduled-tasks view with cron presets.
