# Project todos

The canonical checklist lives in the repo root: **`TODO.md`**. This note is for design notes or decisions that affect the todos.

## Summary (from TODO.md)

1. **Set up Python project** under `src/helping_hands`:
   - **Layout:** `lib/` (core), `cli/` (CLI, uses lib), `server/` (app mode, uses lib)
   - **Tooling:** uv, ruff, `ty` type checking, pre-commit
   - **CI/CD:** Push/PR pipeline runs uv sync, tests, Ruff; E2E integration is opt-in and push-safe in matrix
   - **Tests:** pytest under `tests/`, run in CI

2. **Dockerise app mode and add Compose:** Dockerfile for the app; `compose.yaml` with main server, Celery workers, Redis, Postgres, and Flower.

3. **Autodocs generation and serving on GitHub:** Generate API docs from docstrings (e.g. Sphinx/MkDocs), build in CI, publish to GitHub Pages.

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
- `goose` and `geminicli` CLI backends are now fully implemented with two-phase subprocess flow, streaming, heartbeat/idle-timeout controls, and auto-derived provider/model env wiring.
- Cron-scheduled submissions are now supported via `ScheduleManager` (RedBeat + Redis metadata) with server CRUD endpoints and a `scheduled_build` Celery task.
- `ollama` provider wrapper added to `lib/ai_providers/`, completing the five-provider set (openai, anthropic, google, litellm, ollama).
- `lib/meta/tools/filesystem.py` now has comprehensive test coverage (40 tests in `test_meta_tools_filesystem.py`): path traversal prevention, symlink escape rejection, read/write/mkdir/exists operations, and truncation behavior.
- All CLI hand methods with non-trivial business logic now have Google-style docstrings for mkdocstrings API reference completeness.
- GitHub API calls in `github.py` are now wrapped with `GithubException` handling — clear error messages with HTTP status, detail, and actionable hints (auth, rate limits, 404s, validation failures).
- E2E hardening complete: branch collision handling (switch to existing branch instead of failing), optional draft PR mode (`HELPING_HANDS_DRAFT_PR` env var), and idempotency guard (detect/reuse existing open PR for head branch via `find_open_pr_for_branch`).
- `Config` now validates `repo` format (filesystem path or `owner/repo` pattern) and warns on unexpected `model` name patterns via `__post_init__`.
- `BuildRequest` and `ScheduleRequest` now validate input at the API boundary: `repo_path` and `prompt` require `min_length=1`, `max_iterations` has `ge=1, le=100`, `pr_number` has `ge=1`, and `ScheduleRequest.cron_expression` validates syntax via `croniter`.
- Health check functions (`_check_redis_health`, `_check_db_health`, `_check_workers_health`, `_resolve_worker_capacity`) now log exceptions at warning level with full traceback for production observability.
- Obsidian `AGENT.md` is now a conventions summary for vault readers instead of a bare redirect.
- `ScheduleManager` now has comprehensive unit tests (22 tests with mocked Redis/RedBeat) covering CRUD, enable/disable, record_run, and trigger_now.
- Celery helper functions (`_redact_sensitive`, `_github_clone_url`, `_repo_tmp_dir`, `_trim_updates`, `_append_update`, `_UpdateCollector`) now have unit tests.
- Skills payload runner functions (`_run_python_code`, `_run_python_script`, `_run_bash_script`, `_run_web_search`, `_run_web_browse`) and internal parse helpers now have validation tests.
- `_run_bash_script()` now validates that at least one of `script_path`/`inline_script` is a non-empty string (previously accepted empty payloads).
- `default_prompts.py` is now documented in MkDocs API reference (`docs/api/lib/default_prompts.md` + `mkdocs.yml` nav).
- All four CLI hand implementations (`claude.py`, `codex.py`, `goose.py`, `gemini.py`) now have dedicated unit tests in `tests/test_cli_hands.py` covering model filtering, auth detection, fallback/retry logic, failure parsing, sandbox auto-detection, and provider injection. `placeholders.py` and `default_prompts.py` also have test files.
- AGENT.md dependency table now clarifies that `redis` is a transitive dependency (via `celery[redis]`) and `croniter` is explicitly in `pyproject.toml` under the server extra.
- MCP server `read_file` exception handler ordering fixed — `UnicodeError` (subclass of `ValueError`) now caught before `ValueError` for correct binary file error messages.
- MCP server and server app internal helpers now have dedicated edge-case/unit tests (`test_mcp_server.py` +17, `test_server_app_helpers.py` +47), bringing total test count to 488.
