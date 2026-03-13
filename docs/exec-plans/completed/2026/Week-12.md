# Week 12 (Mar 13 – Mar 19, 2026)

Per-task GitHub token override, dead code cleanup, constant docstrings, security fix, and input validation.

---

## Mar 13 — Per-task GitHub token, dead code cleanup, constant docstrings (v147)

Added `github_token: str = ""` field to `Config` dataclass with `HELPING_HANDS_GITHUB_TOKEN` env var support in `Config.from_env()`. Wired `config.github_token` to `GitHubClient(token=...)` in all 3 call sites (`base.py`, `e2e.py`, `cli/base.py`). Added `--github-token` CLI argument in `cli/main.py` that overrides the env var, passed through Config overrides for both E2E and backend code paths. Added `github_token` field to server `BuildRequest` and `ScheduleRequest` models in `app.py`, wired through Celery `build_feature()` task parameter, and propagated via `ScheduledTask` in `schedules.py`. Removed dead `if cmd else "cli"` fallbacks in `generate_pr_description()` (line 333) and `generate_commit_message()` (line 635) in `pr_description.py` — `cmd` cannot be None at those points due to early returns. Added docstrings for `_COMMIT_MSG_DIFF_LIMIT` and `_COMMIT_MSG_TIMEOUT` constants in `pr_description.py`. **3563 passing tests (+21 new: 7 Config, 4 Hand passthrough, 4 CLI arg, 2 cli_label, 6 constant tests), 80 skipped.**

## Mar 13 (cont.) — Security fix: remove hardcoded DB credentials, GitHubClient input validation (v148)

**Security fix:** Removed hardcoded PostgreSQL connection string with plaintext credentials from `_get_db_url_writer()` in `celery_app.py`. The function now raises `RuntimeError` when `DATABASE_URL` is not set or is empty/whitespace, enforcing secure-by-default configuration. Added `_validate_branch_name()` helper to `github.py` (rejects empty/whitespace-only branch names with `ValueError`), consistent with existing `_validate_full_name()` pattern. Wired validation into `create_branch()`, `switch_branch()`, and `fetch_branch()`. Added empty-message validation to `add_and_commit()` and empty-name/email validation to `set_local_identity()`. **3582 passing tests (+19 new: 5 `_get_db_url_writer`, 5 `_validate_branch_name`, 6 branch validation, 2 commit validation, 4 identity validation), 80 skipped.**

## Mar 13 (cont.) — Git subprocess timeouts, clone URL validation, error message redaction (v149)

**Robustness hardening:** Added `_GIT_READ_TIMEOUT_S = 30` constant to `base.py` and applied `timeout=` parameter to `_run_git_read()` with `TimeoutExpired` catch (returns empty string + warning log), preventing indefinite blocking on hung git processes. Imported and used the same constant in `cli/base.py` `_repo_has_changes()` with `TimeoutExpired` catch (returns `False`). Added `_validate_repo_spec()` helper to both `cli/main.py` and `celery_app.py` — validates `owner/repo` format before embedding into URL strings in `_github_clone_url()`, rejecting empty, whitespace-only, and malformed specs with `ValueError`. **Security:** Removed raw env var value from `_base_command()` `shlex.split()` error message to prevent potential token/secret exposure in logs. **3599 passing tests (+17 new: 3 constant, 3 timeout, 2 repo_has_changes timeout, 7+5 validate_repo_spec, 2+2 clone URL, 1 redaction), 80 skipped.**

## Mar 13 (cont.) — GitHubClient method input validation hardening (v150)

Completed input validation coverage for all public `GitHubClient` methods. Added title/head/base validation to `create_pr()` (reuses `_validate_branch_name()` for head/base, inline non-empty check for title). Added `_VALID_PR_STATES` frozenset constant and state enum validation to `list_prs()` (rejects values not in `{"open", "closed", "all"}`). Added ref non-empty validation to `get_check_runs()`. Added PR number positive validation and body non-empty validation to `upsert_pr_comment()` (matching `get_pr()`/`update_pr_body()` pattern). **3619 passing tests (+20 new: 6 create_pr, 7 list_prs state, 3 get_check_runs, 4 upsert_pr_comment), 80 skipped.**

## Mar 13 (cont.) — Input type validation for filesystem, tool/skill selection, truncation (v151)

**Input validation hardening:** Added runtime type validation to four public functions that accepted typed parameters but didn't validate at runtime. `normalize_relative_path()` in `filesystem.py` now raises `TypeError` when called with non-string values (None, int, list, dict) instead of producing cryptic `AttributeError` at `.strip()`. `normalize_tool_selection()` in `registry.py` and `normalize_skill_selection()` in `skills/__init__.py` now raise `TypeError` when called with dict, set, or int values — previously a `dict` input would silently process dict keys as tokens via `list(values)`. `_truncate_summary()` in `cli/base.py` now raises `ValueError` when `limit < 1`, matching the `_truncate_diff` pattern (v140). **3644 passing tests (+28 new: 6 filesystem, 8 tool selection, 8 skill selection, 6 truncation), 80 skipped.**

## Mar 13 (cont.) — Remove stale ty: ignore comments (v152)

**CI fix:** Removed 7 stale `ty: ignore` suppression comments across 3 files that were triggering `unused-ignore-comment` warnings in `ty check`. The underlying issues (`unknown-argument` on ChatOpenAI kwargs, `unresolved-attribute` on Celery signal, `invalid-assignment` on conditional None fallbacks) were resolved in newer `ty` versions. Added 5 regression guard tests including a codebase-wide scan preventing reintroduction. **3649 passing tests (+5 new: 2 model_provider, 1 celery_app, 1 schedules, 1 codebase-wide), 82 skipped.**

---

**Week summary:** Feature addition (per-task GitHub token override) flowing from CLI/server through Config to GitHubClient, dead code cleanup, constant docstring consistency, security fix removing hardcoded database credentials, input validation for GitHubClient branch/commit/identity methods, git subprocess timeout protection, clone URL format validation, error message redaction, comprehensive GitHubClient method input validation hardening, runtime type validation for filesystem/tool/skill/truncation functions, and CI fix removing stale `ty: ignore` comments. Grew from 3542 to 3649 backend tests.
