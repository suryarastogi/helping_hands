# Week 12 (Mar 13 – Mar 19, 2026)

Per-task GitHub token override, dead code cleanup, constant docstrings, security fix, and input validation.

---

## Mar 13 — Per-task GitHub token, dead code cleanup, constant docstrings (v147)

Added `github_token: str = ""` field to `Config` dataclass with `HELPING_HANDS_GITHUB_TOKEN` env var support in `Config.from_env()`. Wired `config.github_token` to `GitHubClient(token=...)` in all 3 call sites (`base.py`, `e2e.py`, `cli/base.py`). Added `--github-token` CLI argument in `cli/main.py` that overrides the env var, passed through Config overrides for both E2E and backend code paths. Added `github_token` field to server `BuildRequest` and `ScheduleRequest` models in `app.py`, wired through Celery `build_feature()` task parameter, and propagated via `ScheduledTask` in `schedules.py`. Removed dead `if cmd else "cli"` fallbacks in `generate_pr_description()` (line 333) and `generate_commit_message()` (line 635) in `pr_description.py` — `cmd` cannot be None at those points due to early returns. Added docstrings for `_COMMIT_MSG_DIFF_LIMIT` and `_COMMIT_MSG_TIMEOUT` constants in `pr_description.py`. **3563 passing tests (+21 new: 7 Config, 4 Hand passthrough, 4 CLI arg, 2 cli_label, 6 constant tests), 80 skipped.**

## Mar 13 (cont.) — Security fix: remove hardcoded DB credentials, GitHubClient input validation (v148)

**Security fix:** Removed hardcoded PostgreSQL connection string with plaintext credentials from `_get_db_url_writer()` in `celery_app.py`. The function now raises `RuntimeError` when `DATABASE_URL` is not set or is empty/whitespace, enforcing secure-by-default configuration. Added `_validate_branch_name()` helper to `github.py` (rejects empty/whitespace-only branch names with `ValueError`), consistent with existing `_validate_full_name()` pattern. Wired validation into `create_branch()`, `switch_branch()`, and `fetch_branch()`. Added empty-message validation to `add_and_commit()` and empty-name/email validation to `set_local_identity()`. **3582 passing tests (+19 new: 5 `_get_db_url_writer`, 5 `_validate_branch_name`, 6 branch validation, 2 commit validation, 4 identity validation), 80 skipped.**

## Mar 13 (cont.) — Empty command validation, web timeout cap, OSError handling (v149)

Added empty command list validation to `_run_command()` in `command.py` — raises `ValueError` for empty lists, preventing `IndexError` in the `FileNotFoundError` handler at `command[0]`. Added `_MAX_WEB_TIMEOUT_S = 300` module-level constant in `web.py` with warning log when clamping, applied to both `search_web()` and `browse_url()`, consistent with `_MAX_GIT_TIMEOUT` pattern in `github.py`. Added `OSError` catch with debug logging to all four `subprocess.run()` calls in `_get_diff()` and `_get_uncommitted_diff()` in `pr_description.py`, handling permission denied, broken symlinks, etc. gracefully alongside the existing `FileNotFoundError` handling. **3597 passing tests (+15 new: 3 command validation, 3 constant value/type/sign, 5 search/browse timeout cap, 4 OSError handling), 80 skipped.**

---

**Week summary:** Feature addition (per-task GitHub token override) flowing from CLI/server through Config to GitHubClient, dead code cleanup, constant docstring consistency, security fix removing hardcoded database credentials, input validation for GitHubClient branch/commit/identity methods, command execution input validation, web tool timeout safety cap, and subprocess OSError robustness. Grew from 3542 to 3597 backend tests.
