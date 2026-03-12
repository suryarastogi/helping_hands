# Week 11 (Mar 10 – Mar 12, 2026)

Hardening and code quality week. DRY extraction, assert cleanup, input validation, defensive guards, debug logging, test isolation fixes, git operation hardening, type safety, boilerplate line coverage, web helper test coverage, frontend form validation, network error handling, constant extraction. Grew from 3031 to 3835 backend tests, 153 to 178 frontend tests.

---

## Mar 10 — Dead code cleanup, validation, coverage (v104–v118)

Dead code cleanup (4 modules), server routing completion (docker-sandbox-claude), E2E draft PR support, Celery helper extraction, health check tests, server helper unit tests, ty type checker in CI, Claude CLI emitter hardening (non-dict defense, tool summarization, token usage), Hand World factory/incinerator theme, input validation hardening (file size limits, field max_length, distinct error messages), CLI base test coverage (render/finalize/verbose), code quality (DRY extraction, shlex error wrapping, exception logging), defensive guards (empty-cmd, LangGraph defensive access), safety hardening (max_file_size, field limits, _float_env warnings). **3031 → 3543 tests (backend), 153 → 169 tests (frontend).**

## Mar 11 — DRY validators, assert guards, debug logging, git hardening (v119–v124)

DRY validator extraction (`_ToolSkillValidatorMixin` with `max_length=50`), NaN-safe frontend parsing, assert→ValueError guards in base.py, CLI base test isolation fix, hook fix fallback coverage, silent exception logging across 6 modules, assert→RuntimeError in docker_sandbox_claude.py/command.py/e2e.py/schedules.py, repo_root validation in filesystem.py, MCP input validation, ScheduledTask.from_dict hardening, Claude CLI `_summarize_tool` expansion (Skill/CronCreate/CronDelete/CronList/EnterWorktree/ExitWorktree), `_repo_has_changes` debug logging, `_run_git()` timeout protection (configurable via `HELPING_HANDS_GIT_TIMEOUT`), `_validate_full_name()` format validation in `GitHubClient.get_repo()`. **3543 → 3243 tests (backend).** Note: test count decrease reflects consolidation of test environment (celery/redbeat tests now skipped when extras not installed).

## Mar 11 (cont.) — Type safety, timeout bounds, boilerplate test coverage (v125)

Added `ScheduleManager` return type annotation to `_get_schedule_manager()` in `server/app.py` with `TYPE_CHECKING` import and typed module-level variable. Added `_MAX_GIT_TIMEOUT` (3600s) upper bound cap to `_git_timeout()` in `lib/github.py` with warning log for values exceeding the cap. Added direct test coverage for `_is_boilerplate_line()` in `pr_description.py` (bracket banners, numbered lists, bullets, all 18 boilerplate prefixes, case insensitivity, non-boilerplate lines). Consolidated daily plan files (2026-03-10, 2026-03-11) already present in Week-11. **3243 → 3278 tests (backend).**

## Mar 11 (cont.) — Input validation hardening and web helper test coverage (v126)

Added `min_length=1` to `BuildRequest` and `ScheduleRequest` `repo_path` and `prompt` fields to reject empty strings. Added mutual exclusivity validation to `_run_bash_script` in registry.py (exactly one of `script_path`/`inline_script` required). Added direct test coverage for `_as_string_keyed_dict` (5 tests: valid dict, empty dict, non-dict types, non-string keys, mixed keys) and `_require_http_url` host validation (6 tests: no host, with port, ftp scheme, whitespace stripping). **3278 → 3300 tests (backend).**

---

## Mar 11 (cont.) — AI provider and server helper input validation (v127)

Hardened `normalize_messages()` in `ai_providers/types.py` to reject non-Mapping items in message sequences with a clear `TypeError` (previously crashed with `AttributeError` on `.get()`). Added empty-model `ValueError` guard to `AIProvider.complete()` to prevent silent failures when no model is specified and `default_model` is empty/whitespace. Added `_MAX_TASK_KWARGS_LEN` (1MB) size guard to `_parse_task_kwargs_str()` in `server/app.py` with warning log, preventing parsing of unreasonably large payloads. **3300 → 3310 tests (backend).**

## Mar 11 (cont.) — Robustness hardening (v128)

Hardened `_load_meta()` in `schedules.py` to catch corrupted Redis data (`json.JSONDecodeError`, `ValueError`, `TypeError`) with warning log and graceful `None` return instead of crashing. Added `_MAX_ITERATIONS` constant (1000) to `_BasicIterativeHand` in `iterative.py` with warning log when clamping, preventing accidental runaway iteration loops. Added `OSError` catch to `_apply_inline_edits()` in `iterative.py` with warning-level logging (previously only caught `ValueError` for invalid paths; now also handles permission denied, disk full, etc.). **3310 → 3312 tests (backend).**

## Mar 11 (cont.) — Exception debug logging and Goose env test coverage (v129)

Added debug logging (`logger.debug("run_async raised non-AssertionError", exc_info=True)`) to the two remaining silent `except Exception: raise` handlers in `atomic.py` and `iterative.py`, making all exception handlers in the codebase consistently log before suppressing or re-raising. Added comprehensive test coverage for `GooseCLIHand._build_subprocess_env()` (10 tests: GH_TOKEN/GITHUB_TOKEN propagation, missing token RuntimeError, provider/model from config, env overrides, OLLAMA_HOST injection for ollama provider, default model fallback). Added debug logging verification tests for both atomic.py and iterative.py. **3312 → 3304 passing tests (backend; total 3336 including 32 skipped).**

---

## Mar 11 (cont.) — Defensive CI response handling and frontend validation (v130)

Replaced direct key access with defensive `.get()` defaults in `_poll_ci_checks()` and `_ci_fix_loop()` for GitHub API responses (`result["conclusion"]` → `result.get("conclusion", "pending")`, `check_result["total_count"]` → `check_result.get("total_count", 0)`) to prevent `KeyError` on malformed payloads. Added frontend form validation: `submitRun()` now validates repo_path/prompt emptiness before API call, `saveSchedule()` validates name/cron/repo_path/prompt. Exported and tested `statusBlinkerColor()` (7 tests: ok/fail/run/idle tones). Added backend tests for malformed CI responses (7 tests) and frontend form validation component tests (2 tests). **3304 backend tests (unchanged), 169 → 178 frontend tests.**

## Mar 11 (cont.) — Network error handling, clone depth validation, Google empty messages guard (v131)

Wrapped `urlopen()` calls in `search_web()` and `browse_url()` with try-except for `HTTPError` and `URLError`, converting to `RuntimeError` with user-friendly messages and debug logging. Added `depth > 0` validation to `GitHubClient.clone()` (raises `ValueError` for zero/negative depth instead of passing invalid value to git subprocess). Added empty messages guard to `GoogleProvider._complete_impl()` (raises `ValueError` when all messages have empty content instead of sending empty request to API). **3304 → 3329 backend tests (3321 passed, 8 new tests + 2 existing test reductions from structure tests).**

## Mar 11 (cont.) — CLI model None guard, worker capacity tests, LangGraph test gaps (v132)

Fixed `_resolve_cli_model()` in `cli/base.py` and `cli/opencode.py` to treat `"None"` (produced by `str(None)`) as equivalent to empty/default, preventing the literal string `"None"` from being passed to CLI subprocesses. Added comprehensive `_resolve_worker_capacity()` test coverage (13 tests: env var valid/non-numeric/zero/negative/whitespace/priority/second-var, celery stats valid/non-dict-worker/non-int-concurrency/zero-concurrency/non-dict-pool, default fallback). Added LangGraph test coverage: `run()` with empty/missing/None messages (3 tests), `_build_agent` streaming=True assertion (1 test), `stream()` with chunk lacking content attribute (1 test). **3329 → 3361 backend tests (3328 passed, 33 skipped).**

## Mar 11 (cont.) — Warning logging, git-not-found handling, write_text_file OSError safety (v133)

Added `logger.warning()` to `_timeout_seconds()` and `_diff_char_limit()` in `pr_description.py` for invalid (non-numeric) and non-positive env var values — previously these silently fell back to defaults, making misconfiguration invisible. Wrapped `subprocess.run()` calls in `_get_diff()` and `_get_uncommitted_diff()` with try-except for `FileNotFoundError`, returning empty string gracefully when git is not installed instead of crashing. Wrapped `write_text_file()` in `filesystem.py` with OSError catch, converting raw system errors (permission denied, disk full) into `RuntimeError` with file path context. **3361 → 3369 backend tests (3336 passed, 33 skipped).**

## Mar 11 (cont.) — Input validation and test coverage gaps (v134)

Hardened `_parse_str_list()` in both `registry.py` and `iterative.py` to reject empty/whitespace-only strings with `ValueError` and strip whitespace from valid items — previously accepted silently, inconsistent with `_parse_optional_str` which already strips and rejects empty strings. Added `_load_env_files()` tilde expansion test coverage (verifying `expanduser()` is called before `is_dir()` check). Added direct test coverage for `_collect_celery_current_tasks()` orchestrator in `server/app.py` (7 tests: inspector None, active/reserved task collection, non-helping-hands filtering, missing task ID skip, deduplication across inspect shapes, status fallback for invalid state). **3369 → 3382 backend tests (3780 total including server extras, all passing).**

## Mar 11 (cont.) — Extract magic numbers to constants (v135)

Extracted hardcoded magic numbers into module-level constants for maintainability: `_DEFAULT_EXEC_TIMEOUT_S = 60` and `_DEFAULT_BROWSE_MAX_CHARS = 12000` in `mcp_server.py` (used in `run_python_code`, `run_python_script`, `run_bash_script`, and `web_browse` function signature defaults), and `_USAGE_LOG_INTERVAL_S = 3600.0` in `celery_app.py` (used in `ensure_usage_schedule`). Added tests verifying constant values, type/sign invariants, and function signature defaults. **3382 → 3392 backend tests (7 new MCP constant tests passed, 3 celery constant tests skipped without celery extra).**

---

## Mar 12 — Gitignore cleanup and commit message quality (v136)

Added Playwright/E2E test artifact directories (`frontend/test-results/`, `frontend/playwright-report/`, `frontend/blob-report/`) and `coverage.xml` to `.gitignore`. Added `_is_trivial_message()` validator to `pr_description.py` that rejects trivially short or punctuation-only commit messages (e.g., `feat: -`, `feat: ...`), integrated into both `_parse_commit_message()` (CLI path) and `_commit_message_from_prompt()` (heuristic fallback path). Resolved both open TODO.md items. **3376 passing tests (+27 new: 15 `_is_trivial_message`, 5 parse rejection, 4 prompt rejection, 3 gitignore pattern tests), 36 skipped.**

## Mar 12 (cont.) — Health check timeout and API constant extraction (v137)

Extracted six hardcoded health-check timeout values in `server/app.py` to module-level constants: `_KEYCHAIN_TIMEOUT_S` (5), `_USAGE_API_TIMEOUT_S` (10), `_REDIS_HEALTH_TIMEOUT_S` (2), `_DB_HEALTH_TIMEOUT_S` (3), `_CELERY_HEALTH_TIMEOUT_S` (2.0), `_CELERY_INSPECT_TIMEOUT_S` (1.0). Extracted duplicated Anthropic usage API constants (`_ANTHROPIC_USAGE_URL`, `_ANTHROPIC_BETA_HEADER`, `_USAGE_USER_AGENT`) to module-level in both `server/app.py` and `server/celery_app.py`, replacing identical hardcoded strings. Added cross-module sync test to prevent drift. **3835 passing tests (+17 new: 12 app.py constant tests, 5 celery_app.py constant tests), 2 skipped.**

## Mar 12 (cont.) — Hand base, CLI base, and CLI main constant extraction (v138)

Extracted hardcoded magic numbers to module-level constants across three core files. In `base.py`: `_DEFAULT_BASE_BRANCH` ("main"), `_DEFAULT_GIT_USER_NAME` ("helping-hands[bot]"), `_DEFAULT_GIT_USER_EMAIL`, `_DEFAULT_CI_WAIT_MINUTES` (3.0), `_DEFAULT_CI_MAX_RETRIES` (3), `_BRANCH_PREFIX` ("helping-hands/"), `_UUID_HEX_LENGTH` (8), `_MAX_OUTPUT_DISPLAY_LENGTH` (4000), `_FILE_LIST_PREVIEW_LIMIT` (200), `_LOG_TRUNCATION_LENGTH` (200). In `cli/base.py`: `_PROCESS_TERMINATE_TIMEOUT_S` (5), `_CI_POLL_INTERVAL_S` (30.0), `_PR_DESCRIPTION_TIMEOUT_S` (300). In `cli/main.py`: `_DEFAULT_CLONE_DEPTH` (1), `_TEMP_CLONE_PREFIX` ("helping_hands_repo_"). **3436 passing tests (+31 new constant value/type/sign invariant tests), 37 skipped.**

---

**Week summary:** Systematic hardening across the codebase. Replaced all remaining `assert` statements in production code with explicit guards. Added debug logging to all silent exception handlers (including the final two bare re-raises in atomic.py/iterative.py in v129). Expanded Claude CLI tool summarization. Consolidated validators via mixin extraction. Added input validation to MCP server tools and server request models. Hardened git subprocess operations with timeout protection and input format validation. Added type annotations and test coverage for previously untested helpers. Added empty-string rejection to server request models and mutual exclusivity validation to bash script runner. Hardened AI provider message normalization and model validation. Added comprehensive test coverage for GooseCLIHand._build_subprocess_env (v129). Added defensive `.get()` for CI response handling and frontend form validation (v130). Added network error handling for web tools, clone depth validation, and Google provider empty messages guard (v131). Fixed CLI model None guard and added worker capacity + LangGraph test coverage (v132). Added warning logging for silent env var fallbacks, git-not-found error handling, and write_text_file OSError wrapping (v133). Hardened `_parse_str_list` with empty/whitespace rejection, added `_load_env_files` tilde expansion test, added `_collect_celery_current_tasks` direct test coverage (v134). Extracted hardcoded magic numbers to module-level constants in `mcp_server.py` and `celery_app.py` with tests (v135). Gitignore cleanup for Playwright test artifacts and commit message quality hardening with `_is_trivial_message()` rejection (v136). Extracted health-check timeout constants and DRY Anthropic API constants in `server/app.py` and `server/celery_app.py` (v137). Extracted hardcoded magic numbers to module-level constants in Hand base, CLI base, and CLI main (v138).
