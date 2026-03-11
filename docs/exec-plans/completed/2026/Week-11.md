# Week 11 (Mar 10 – Mar 11, 2026)

Hardening and code quality week. DRY extraction, assert cleanup, input validation, defensive guards, debug logging, test isolation fixes, git operation hardening, type safety, boilerplate line coverage, web helper test coverage, frontend form validation, network error handling. Grew from 3031 to 3361 backend tests, 153 to 178 frontend tests.

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

---

**Week summary:** Systematic hardening across the codebase. Replaced all remaining `assert` statements in production code with explicit guards. Added debug logging to all silent exception handlers (including the final two bare re-raises in atomic.py/iterative.py in v129). Expanded Claude CLI tool summarization. Consolidated validators via mixin extraction. Added input validation to MCP server tools and server request models. Hardened git subprocess operations with timeout protection and input format validation. Added type annotations and test coverage for previously untested helpers. Added empty-string rejection to server request models and mutual exclusivity validation to bash script runner. Hardened AI provider message normalization and model validation. Added comprehensive test coverage for GooseCLIHand._build_subprocess_env (v129). Added defensive `.get()` for CI response handling and frontend form validation (v130). Added network error handling for web tools, clone depth validation, and Google provider empty messages guard (v131). Fixed CLI model None guard and added worker capacity + LangGraph test coverage (v132). Added warning logging for silent env var fallbacks, git-not-found error handling, and write_text_file OSError wrapping (v133).
