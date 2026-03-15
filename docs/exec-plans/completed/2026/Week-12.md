# Week 12 (Mar 13 – Mar 19, 2026)

Per-task GitHub token override, dead code cleanup, constant docstrings, security fix, input validation, CI status enums, and test coverage.

---

## Mar 15 — DRY truncation suffix, code fences, bool-lower helper (v211)

**`_TRUNCATION_SUFFIX` constant + `_truncation_note()` helper:** Extracted the repeated `"\n[truncated]" if truncated else ""` pattern from 6 locations in `iterative.py` into a module-level `_TRUNCATION_SUFFIX` constant and a `_truncation_note()` staticmethod.

**Code fence constants:** Extracted `_FENCE_TEXT` (`"```text"`), `_FENCE_JSON` (`"```json"`), `_FENCE_CLOSE` (`"```"`) constants replacing 7+ inline code-fence markers in tool result formatting methods.

**`_bool_lower()` staticmethod:** Extracted the repeated `str(bool_val).lower()` pattern from 4 locations (`timed_out`, `source_truncated`, 2× `interrupted`) into a named `_bool_lower()` helper.

**`tests/test_v211_dry_truncation_fences_bool_lower.py`:** 31 tests verifying constants exist with correct values, helpers return correct results, and formatting methods reference the new constants (no inline duplicates).

**31 new tests. 5174 passed, 216 skipped.**

---

## Mar 15 — Hook markers constant, validation + github_url test coverage (v210)

**`_GIT_HOOK_FAILURE_MARKERS` constant:** Extracted inline `markers` tuple from `_is_git_hook_failure()` in `base.py` to a module-level constant with docstring.

**`tests/test_validation.py`:** 21 dedicated unit tests for `require_non_empty_string` and `require_positive_int` — valid returns, empty/whitespace rejection, error message formatting, unicode, multiline, zero/negative values.

**`tests/test_github_url.py`:** 33 dedicated unit tests for `validate_repo_spec`, `build_clone_url`, `redact_credentials`, `noninteractive_env`, and module constants.

**`tests/test_v210_hook_markers_validation_github_url.py`:** 16 versioned tests verifying constant extraction, module contracts, and API surfaces.

**70 new tests. 5143 passed, 216 skipped.**

---

## Mar 15 — CI status enums, boilerplate optimization, stream event constant (v209)

**`CIConclusion(StrEnum)`:** Replaced 5 hardcoded CI conclusion strings in `github.py` `get_check_runs()` with `CIConclusion` enum (5 members). Added `CI_CONCLUSIONS_IN_PROGRESS` frozenset and `_CI_RUN_FAILURE_CONCLUSIONS` frozenset for check-run failure conclusions.

**`CIFixStatus(StrEnum)`:** Replaced 7 hardcoded CI fix loop status strings in `cli/base.py` with `CIFixStatus` enum (7 members). Used across `_ci_fix_loop`, `_poll_ci_checks`, `_build_ci_fix_prompt`, and `_format_ci_fix_message`.

**Boilerplate prefix optimization:** Added `_BOILERPLATE_PREFIXES_LOWER` pre-computed tuple in `pr_description.py` to avoid repeated `.lower()` calls inside `_is_boilerplate_line()`.

**`_LANGCHAIN_STREAM_EVENT` constant:** Extracted duplicated `"on_chat_model_stream"` string from `langgraph.py` and `iterative.py` into a shared module-level constant.

**36 new tests. 5073 passed, 216 skipped.**

---

## Mar 15 — PR status enum, validation cleanup, DRY metadata builder (v208)

**`PRStatus(StrEnum)`:** Replaced 5 module-level string constants (`_PR_STATUS_CREATED`, etc.) + 2 frozensets + 7 ad-hoc inline status strings ("no_repo", "not_git_repo", "no_github_origin", "precommit_failed", "missing_token", "git_error", "error") with a single `PRStatus(StrEnum)` enum with 12 members. Module-level `PR_STATUSES_WITH_URL` and `PR_STATUSES_SKIPPED` frozensets. Backward-compatible aliases preserve all existing imports.

**Validation cleanup:** `_build_generic_pr_body` `commit_sha`/`stamp_utc` validation now delegates to `require_non_empty_string()` (replacing manual `isinstance()`/`.strip()` checks).

**DRY `_pr_result_metadata()`:** Extracted static helper replacing 3 identical `metadata.update({"pr_status": ..., "pr_url": ..., ...})` blocks in `_push_to_existing_pr`, `_create_pr_for_diverged_branch`, and `_finalize_repo_pr`.

**38 new tests. 5037 passed, 216 skipped.**

---

## Mar 15 — DRY shared validation helpers (v207)

**Shared `validation.py` module:** Created `src/helping_hands/lib/validation.py` with two helpers: `require_non_empty_string(value, name)` and `require_positive_int(value, name)`. These consolidate the two most duplicated validation patterns in the codebase.

**`require_non_empty_string`:** Replaced 23 inline `if not X or not X.strip(): raise ValueError(...)` guards across 7 files: `github.py` (8 sites), `mcp_server.py` (6 sites), `base.py` (4 sites), `pr_description.py` (3 sites), `github_url.py` (1 site), `app.py` (`_validate_path_param` delegation, 1 site).

**`require_positive_int`:** Replaced 14 inline `if value <= 0: raise ValueError(...)` guards across 5 files: `github.py` (5 sites), `web.py` (4 sites), `filesystem.py` (2 sites), `pr_description.py` (2 sites), `command.py` (1 site).

**36 new tests. 4999 passed, 216 skipped.**

---

## Mar 15 — DRY payload validators, normalize selection, URL error handling (v206)

**DRY payload validators:** Removed 3 duplicated `_parse_str_list`/`_parse_positive_int`/`_parse_optional_str` static methods from `_BasicIterativeHand` in `iterative.py`, replacing them with class-level `staticmethod()` assignments that delegate to the canonical implementations in `registry.py`.

**DRY `_normalize_and_deduplicate`:** Extracted shared helper in `registry.py` that consolidates the identical normalize/deduplicate logic previously duplicated between `normalize_tool_selection()` and `normalize_skill_selection()`. Both functions now delegate to the shared helper with a `label` parameter for error messages.

**DRY `_raise_url_error`:** Extracted shared helper in `web.py` that consolidates the duplicated `HTTPError`/`URLError` → `RuntimeError` conversion pattern (with debug logging) from both `search_web()` and `browse_url()`.

**30 new tests. Updated `__all__` test for registry.py. 4967 passed, 212 skipped.**

---

## Mar 15 — DRY form defaults, truthy values, inline import, tool dispatch (v204)

**Fix form default mismatch:** `enqueue_build_form` used hardcoded `"codexcli"` as backend default instead of `_DEFAULT_BACKEND` (`"claudecodecli"`). Also replaced hardcoded `6` → `_DEFAULT_MAX_ITERATIONS` and `3.0` → `_DEFAULT_CI_WAIT_MINUTES` in both `enqueue_build_form` Form defaults and `_build_form_redirect_query` signature/comparison.

**DRY `_is_running_in_docker`:** Replaced inline `{"1", "true", "yes"}` set with `_TRUTHY_VALUES` import from `config.py`.

**Top-level `import time`:** Moved `import time as _time` from inside `_fetch_claude_usage` function body to module-level `import time`.

**`_TOOL_SUMMARY_KEY_MAP` dispatch table:** Extracted 5-entry dict mapping tool names (`Read`, `Edit`, `Write`, `Glob`, `NotebookEdit`) to their input key for the simple `"ToolName {value}"` pattern, plus `_TOOL_SUMMARY_STATIC` frozenset for parameter-less tools (`TodoWrite`, `CronList`). Refactored `_StreamJsonEmitter._summarize_tool()` to use lookup tables before the custom-format if/elif chain.

**52 tests (40 new, 12 skipped without fastapi). Updated `__all__` test for claude.py. 4913 passed, 208 skipped.**

---

## Mar 15 — DRY auth failure detection + text truncation helper (v203)

**DRY `_detect_auth_failure` helper:** Extracted `_detect_auth_failure(output, extra_tokens=())` → `(bool, str)` in `cli/base.py`, encapsulating the 3-line tail-extraction + lowercase + token-check pattern previously duplicated in `claude.py`, `codex.py`, `gemini.py`, and `opencode.py`. Removed direct `_AUTH_ERROR_TOKENS` and `_FAILURE_OUTPUT_TAIL_LENGTH` imports from all 4 subclass files.

**DRY `_truncate_with_ellipsis` helper:** Extracted `_truncate_with_ellipsis(text, limit)` in `cli/base.py`, replacing 4× inline `text[:limit - 3] + "..."` patterns in `claude.py`'s `_StreamJsonEmitter`.

**50 new tests, 4873 passed, 196 skipped. Updated 3 existing test files to reflect the new encapsulation.**

---

## Mar 15 — DRY Python version default + command-not-found messages (v202)

**DRY `_DEFAULT_PYTHON_VERSION` in MCP server:** Replaced 2× hardcoded `"3.13"` default values in `mcp_server.py` (`run_python_code`, `run_python_script`) with import of `_DEFAULT_PYTHON_VERSION` from `command.py`, establishing single source of truth.

**DRY `_command_not_found_message`:** Enhanced the base class `_TwoPhaseCLIHand._command_not_found_message()` in `cli/base.py` to include the Docker rebuild hint (`_DOCKER_REBUILD_HINT_TEMPLATE.format(command)`) using the `command` parameter. Removed 5 redundant overrides from `claude.py`, `codex.py`, `gemini.py`, `goose.py`, and `opencode.py`. Removed 4 now-unused `_DOCKER_REBUILD_HINT_TEMPLATE` imports from subclass files. `docker_sandbox_claude.py` retains its own override (different sandbox-specific message).

**39 new tests passed (5 MCP server constant import/identity/value, 7 base message content/source, 10 subclass no-override/inheritance, 15 subclass message content, 2 Docker sandbox override verification). Updated 4 existing v201 tests to reflect base-class consolidation.**

---

## Mar 15 — DRY Docker hint message templates (v201)

**DRY Docker env hint:** Extracted `_DOCKER_ENV_HINT_TEMPLATE` string template in `cli/base.py` for the auth failure Docker remediation message (`"If running app mode in Docker, set {} in .env and recreate server/worker containers."`). Replaced 4× duplicated strings across `claude.py`, `codex.py`, `gemini.py`, and `opencode.py` auth failure handlers.

**DRY Docker rebuild hint:** Extracted `_DOCKER_REBUILD_HINT_TEMPLATE` string template in `cli/base.py` for the command-not-found Docker remediation message (`"If running app mode in Docker, rebuild worker images so the {} binary is installed."`). Replaced 4× duplicated strings across `codex.py`, `gemini.py`, `goose.py`, and `opencode.py` command-not-found handlers.

**24 new tests passed (7 env hint value/format, 7 rebuild hint value/format, 4 env hint cross-module import, 4 rebuild hint cross-module import, 2 __all__ export checks).**

---

## Mar 15 — DRY timestamp helper, truthy env check, UUID hex length (v200)

**DRY timestamp helper:** Extracted `_utc_stamp()` helper function in `base.py` that returns `datetime.now(UTC).replace(microsecond=0).isoformat()`. Replaced 3× inline usages in `base.py` methods (`_update_pr_description`, `_create_pr_for_diverged_branch`, `_finalize_repo_pr`) and 1× in `e2e.py` (`run`). Removed unused `datetime`/`UTC` imports from `e2e.py`.

**DRY celery truthy check:** `celery_app.py` `_VERBOSE` now imports and uses `_TRUTHY_VALUES` frozenset from `config.py` instead of an inline `("1", "true", "yes")` tuple.

**DRY sandbox UUID hex length:** `docker_sandbox_claude.py` `_SANDBOX_UUID_HEX_LENGTH` now delegates to `_UUID_HEX_LENGTH` imported from `base.py` instead of hardcoding `8`.

**4784 backend tests passed (+19 new: 8 `_utc_stamp` value/format/timezone/regex, 3 e2e import identity/source, 3 celery truthy import/identity/source, 5 sandbox UUID value/identity/import/source), 199 skipped.**

---

## Mar 15 — DRY registry.py default constants (v199)

**DRY Python version:** Extracted `_DEFAULT_PYTHON_VERSION = "3.13"` in `command.py`, replacing 2× hardcoded `"3.13"` in `run_python_code()` and `run_python_script()` function defaults.

**DRY search max results:** Extracted `DEFAULT_SEARCH_MAX_RESULTS = 5` in `web.py` as a public constant (added to `__all__`). `search_web()` default now references the named constant.

**DRY registry imports:** `registry.py` now imports `_DEFAULT_SCRIPT_TIMEOUT_S` and `_DEFAULT_PYTHON_VERSION` from `command.py`, and `_DEFAULT_WEB_TIMEOUT_S` and `DEFAULT_SEARCH_MAX_RESULTS` from `web.py`. All 7 hardcoded default literals in the 5 runner wrappers (`_run_python_code`, `_run_python_script`, `_run_bash_script`, `_run_web_search`, `_run_web_browse`) replaced with named constant references.

**5541 backend tests passed (+17 new: 4 _DEFAULT_PYTHON_VERSION value/type/signature, 5 DEFAULT_SEARCH_MAX_RESULTS value/type/positive/__all__/signature, 4 registry import identity, 4 no-hardcoded-literal source checks), 2 skipped.**

---

## Mar 15 — DRY token redaction, ci_wait constant fallback, root __all__, test stub fix (v198)

**DRY token redaction:** Extracted 3 magic numbers from `_redact_token()` in `server/app.py` to named constants: `_REDACT_TOKEN_PREFIX_LEN = 4`, `_REDACT_TOKEN_SUFFIX_LEN = 4`, `_REDACT_TOKEN_MIN_PARTIAL_LEN = 12`. The function now uses these constants instead of hardcoded `4`, `4`, `12` values. Added Google-style docstring with Args/Returns to `_redact_token()`.

**ci_wait constant fallback:** Replaced hardcoded `3.0` in the `getattr(task, "ci_check_wait_minutes", 3.0)` backward-compatibility fallback in `_schedule_to_response()` with `_DEFAULT_CI_WAIT_MINUTES` imported from `server/constants.py`, ensuring the fallback stays in sync with the declared default.

**Root package `__all__`:** Added `__all__ = ["__version__"]` to `src/helping_hands/__init__.py`, completing project-wide explicit `__all__` coverage (all 31 modules now declare `__all__`).

**Test stub fix:** Added missing `github_token` and `reference_repos` fields to `_FakeScheduledTask` in `test_server_app_schedule_response.py`, aligning the test stub with the production `ScheduledTask` dataclass. Updated `test_all_fields_forwarded` to verify `github_token` redaction and `reference_repos` passthrough. Updated `test_task_missing_optional_attrs_uses_defaults` to cover `github_token` and `reference_repos` getattr fallbacks.

**5524 backend tests passed (+22 new: 5 root __all__, 9 redact token constants, 7 redact token behaviour, 1 ci_wait fallback), 2 skipped.**

---

## Mar 15 — DRY field validation bounds, BackendName dedup, bytes-per-MB (v197)

**DRY field validation bounds:** Extracted 7 shared constants to `server/constants.py`: `MAX_ITERATIONS_UPPER_BOUND = 100`, `MIN_CI_WAIT_MINUTES = 0.5`, `MAX_CI_WAIT_MINUTES = 30.0`, `MAX_REPO_PATH_LENGTH = 500`, `MAX_PROMPT_LENGTH = 50_000`, `MAX_MODEL_LENGTH = 200`, `MAX_GITHUB_TOKEN_LENGTH = 500`. `BuildRequest` and `ScheduleRequest` in `app.py` now reference these shared constants instead of duplicated inline literals in `Field()` definitions.

**BackendName deduplication:** Moved `BackendName` type alias above `BuildRequest` class definition. `BuildRequest.backend` now references `BackendName` instead of a duplicated inline `Literal[...]` with the same 10 backend strings. Added `BackendName` to `app.py` `__all__`.

**bytes-per-MB constant:** Extracted `_BYTES_PER_MB = 1024 * 1024` in `filesystem.py`. `_MAX_FILE_SIZE_BYTES` now expressed as `10 * _BYTES_PER_MB` and file size error formatting uses the named constant.

**4736 backend tests passed (+33 new: 10 constant value/type, 1 __all__, 7 BuildRequest bounds, 7 ScheduleRequest bounds, 4 BackendName, 4 _BYTES_PER_MB), 192 skipped.**

---

## Mar 15 — DRY shared defaults, reference_repos validation, usage cache TTL (v196)

**DRY shared defaults:** Extracted `DEFAULT_BACKEND = "claudecodecli"`, `DEFAULT_MAX_ITERATIONS = 6`, `DEFAULT_CI_WAIT_MINUTES = 3.0` to `server/constants.py` as the single source of truth. `BuildRequest`, `ScheduleRequest`, and `ScheduleResponse` in `app.py` now reference the shared constants instead of duplicated literals. `ScheduledTask` dataclass defaults and `from_dict()` fallbacks in `schedules.py` likewise import from the shared source.

**reference_repos validation:** Added `MAX_REFERENCE_REPOS = 10` to `server/constants.py`. `BuildRequest.reference_repos` and `ScheduleRequest.reference_repos` now enforce `max_length=_MAX_REFERENCE_REPOS` via Pydantic `Field()`, preventing unbounded lists from being submitted.

**Usage cache TTL:** Extracted `USAGE_CACHE_TTL_S = 300` with docstring to `server/constants.py`, replacing the local `_USAGE_CACHE_TTL = 300` in `app.py`.

**4723 backend tests passed (+27 new: 7 constant values, 6 app defaults, 6 schedules defaults, 5 reference_repos validation, 2 usage cache TTL, 1 __all__ update), 174 skipped.**

---

## Mar 15 — DRY git identity, browse max chars, clone timeout (v195)

**DRY git identity:** `_E2E_GIT_USER_NAME` and `_E2E_GIT_USER_EMAIL` in `e2e.py` now reference `_DEFAULT_GIT_USER_NAME`/`_DEFAULT_GIT_USER_EMAIL` from `base.py` instead of duplicating the string literals.

**DRY browse max chars:** Extracted `DEFAULT_BROWSE_MAX_CHARS = 12000` in `web.py` as the single source, replacing 3× hardcoded `12000` across `web.py` (`browse_url` default), `registry.py` (browse_url call), and `mcp_server.py` (`_DEFAULT_BROWSE_MAX_CHARS`). Added to `web.py` `__all__` exports.

**DRY clone timeout:** Extracted `GIT_CLONE_TIMEOUT_S = 120` to `github_url.py`, replacing 2× duplicated `_GIT_CLONE_TIMEOUT_S = 120` constants in `cli/main.py` and `celery_app.py`. Both modules now import from the shared source.

**4715 backend tests passed (+15 new: 4 git identity, 6 browse max chars, 5 clone timeout), 156 skipped.**

---

## Mar 15 — DRY timeout constants and PR status sentinels (v194)

**DRY refactoring:** Extracted `_DEFAULT_SCRIPT_TIMEOUT_S = 60` module-level constant in `command.py`, replacing 3× hardcoded `timeout_s: int = 60` defaults across `run_python_code`, `run_python_script`, and `run_bash_script`. Extracted `_DEFAULT_WEB_TIMEOUT_S = 20` in `web.py`, replacing 2× hardcoded defaults across `search_web` and `browse_url`.

**PR status sentinels:** Extracted 5 `_PR_STATUS_*` string constants (`_PR_STATUS_CREATED`, `_PR_STATUS_UPDATED`, `_PR_STATUS_NO_CHANGES`, `_PR_STATUS_DISABLED`, `_PR_STATUS_NOT_ATTEMPTED`) and 2 `_PR_STATUSES_*` frozensets (`_PR_STATUSES_WITH_URL`, `_PR_STATUSES_SKIPPED`) in `base.py`, replacing ~17 scattered string literals across `base.py`, `iterative.py`, and `cli/base.py`. Consumers import from `base.py` ensuring a single source of truth for PR lifecycle status values.

**4700 backend tests passed (+33 new: 6 command timeout, 5 web timeout, 12 PR status sentinels, 4 frozenset, 6 cross-module identity), 155 skipped.**

---

## Mar 15 — DRY auth error tokens, iterative docstrings, frontend a11y (v193)

**DRY refactoring:** Extracted shared `_AUTH_ERROR_TOKENS` tuple constant to `cli/base.py` with `__all__` export, replacing 4× duplicated auth detection string literals across `claude.py`, `codex.py`, `gemini.py`, and `opencode.py`. Each CLI hand now imports the shared constant from `cli/base.py`; backend-specific tokens (e.g. `"anthropic_api_key"` in `claude.py`, `"gemini_api_key"` in `gemini.py`, `"missing bearer or basic authentication"` in `codex.py`) remain local. Added `ClaudeCodeHand._EXTRA_AUTH_TOKENS` class-level constant for Claude-specific tokens.

**Docstrings:** Added Google-style docstrings with Args/Returns/Yields sections to 4 remaining undocumented public methods: `BasicLangGraphHand.run()` and `stream()`, `BasicAtomicHand.run()` and `stream()` in `iterative.py`.

**Frontend accessibility:** Added `aria-label="Repository path"` and `aria-label="Task prompt"` to the inline submission form inputs in `App.tsx`. Added `.catch()` handlers to 3 unhandled `Notification.requestPermission()` and `fetchServerConfig()` promise chains.

**4667 backend tests passed (+37 new: 9 constant value/type, 4 cross-module identity, 4 auth detection, 3 codex/gemini auth, 7+8 LangGraph/Atomic docstring presence/sections), 155 skipped. 180 frontend tests passed (+2 new: aria-label accessibility).**

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

## Mar 13 (cont.) — Subprocess timeouts for push remote and precommit, input validation (v153)

**Robustness hardening:** Added `_GIT_PUSH_REMOTE_TIMEOUT_S = 30` constant to `base.py` and applied `timeout=` parameter to `subprocess.run()` in `_configure_authenticated_push_remote()` with `TimeoutExpired` catch wrapping to `RuntimeError`. Added `_GIT_PRECOMMIT_TIMEOUT_S = 120` constant and applied timeout to `_run_precommit_checks_and_fixes()` subprocess call. Added input validation for `_configure_authenticated_push_remote()` repo/token parameters (non-empty string checks) and `GitHubClient.clone()` `full_name` parameter validation via `_validate_full_name()`. **3666 passing tests (+16 new: 3 push remote timeout constant, 3 precommit timeout constant, 4 push remote validation, 3 clone validation, 3 timeout behavior), 80 skipped.**

## Mar 13 (cont.) — Git subprocess timeouts for pr_description/clone, read_text_file max_chars validation (v154)

**Robustness hardening:** Added `_GIT_DIFF_TIMEOUT_S = 30` constant to `pr_description.py` and applied `timeout=` parameter to all 4 `subprocess.run()` calls in `_get_diff()` (2 calls: base branch diff and HEAD~1 fallback) and `_get_uncommitted_diff()` (2 calls: git add and git diff --cached) with `TimeoutExpired` catch returning empty string + warning log. Added `_GIT_CLONE_TIMEOUT_S = 120` constant to both `cli/main.py` and `celery_app.py`, applied timeout to clone subprocess calls with `TimeoutExpired` catch raising `ValueError` and cleaning up temp directory. Added `max_chars` positive validation to `read_text_file()` in `filesystem.py` — rejects zero/negative values with `ValueError` instead of silently truncating from end via `text[:negative]`. **3687 passing tests (+21 new: 3 diff timeout constant, 7 diff/uncommitted timeout, 3+4 CLI/Celery clone timeout constant, 2+2 clone timeout behavior, 6 max_chars validation), 88 skipped.**

## Mar 13 (cont.) — Input validation and defensive coding hardening (v155)

**Defensive coding:** Added `max_file_size <= 0` → `ValueError` guard in `read_text_file()` in `filesystem.py`, mirroring the `max_chars` validation pattern (v154). Changed `m["content"]` to `m.get("content")` in Google provider `_complete_impl()` to prevent `KeyError` when message dicts lack a "content" key. Added tests for `_get_diff()` fallback paths where first diff returns non-zero/empty stdout and second attempt hits `FileNotFoundError` or `TimeoutExpired`. **3700 passing tests (+14 new: 7 max_file_size validation, 4 Google provider missing content key, 3 _get_diff fallback paths), 88 skipped.**

## Mar 13 (cont.) — Config whitespace stripping, __all__ export, PR body validation (v156)

**Defensive coding:** Added `.strip()` calls to `repo`, `model`, and `github_token` string fields in `Config.from_env()` — whitespace-padded inputs (e.g. from env vars or CLI args with trailing spaces) are now cleaned before assignment, preventing path resolution failures, model lookup mismatches, or token auth errors downstream. Added `__all__ = ["Config"]` to `config.py` for explicit public API declaration, matching the pattern used by all other public modules in the project. Added `backend`/`prompt` empty/whitespace validation to `_build_generic_pr_body()` in `base.py` — empty or whitespace-only values now raise `ValueError` instead of producing malformed PR bodies. Added edge case tests for `_is_git_hook_failure()` (empty string, whitespace-only, plain text without markers). **3716 passing tests (+16 new: 6 Config whitespace, 2 __all__, 4 PR body validation, 3 hook failure edge cases, 1 existing pattern), 88 skipped.**

## Mar 13 (cont.) — Add __all__ exports to 4 modules, enhance normalize_messages docstring (v157)

**API consistency:** Added `__all__` declarations to 4 public modules that were missing them, completing the pattern established in v156 (config.py). `types.py` now exports `["AIProvider", "PromptInput", "normalize_messages"]`. `github.py` exports `["GitHubClient", "PRResult"]`. `filesystem.py` exports 6 public functions (`mkdir_path`, `normalize_relative_path`, `path_exists`, `read_text_file`, `resolve_repo_target`, `write_text_file`). `command.py` exports `["CommandResult", "run_bash_script", "run_python_code", "run_python_script"]`. Enhanced `normalize_messages()` docstring from a one-liner to full Google-style with Args/Returns/Raises sections. **3743 passing tests (+27 new: 5 types.py __all__, 4 github.py __all__, 8 filesystem.py __all__, 6 command.py __all__, 4 docstring sections), 88 skipped.**

## Mar 13 (cont.) — Add __all__ to 4 more modules, extract DuckDuckGo URL constant, filesystem validation (v158)

**API consistency and validation:** Added `__all__` declarations to 4 more modules: `web.py` (5 public symbols: `WebSearchItem`, `WebSearchResult`, `WebBrowseResult`, `search_web`, `browse_url`), `repo.py` (`RepoIndex`), `default_prompts.py` (`DEFAULT_SMOKE_TEST_PROMPT`), `task_result.py` (`normalize_task_result`). Extracted `_DUCKDUCKGO_API_URL = "https://api.duckduckgo.com/"` module-level constant in `web.py` from hardcoded URL in `search_web()`. Added empty/whitespace `ValueError` validation to `normalize_relative_path()` in `filesystem.py` — previously accepted empty strings silently while `resolve_repo_target()` had its own downstream check. Updated `_build_tree_snapshot()` in `iterative.py` to catch `ValueError` from invalid paths instead of checking `if not normalized`. **3772 passing tests (+29 new: 8 web.py __all__, 4 repo.py __all__, 4 default_prompts.py __all__, 4 task_result.py __all__, 4 DuckDuckGo constant, 5 filesystem validation), 88 skipped.**

## Mar 13 (cont.) — Add `__all__` to 8 modules: AI providers, pr_description, model_provider, schedules (v159)

**API consistency:** Added `__all__` declarations to 8 more modules, completing the pattern for all AI provider modules and key hand/server modules. Five AI provider modules (`openai.py`, `anthropic.py`, `google.py`, `litellm.py`, `ollama.py`) each export their provider class and singleton instance (e.g. `["OPENAI_PROVIDER", "OpenAIProvider"]`). `pr_description.py` exports `["PRDescription", "generate_commit_message", "generate_pr_description"]`. `model_provider.py` exports `["HandModel", "build_atomic_client", "build_langchain_chat_model", "resolve_hand_model"]`. `schedules.py` exports `["CRON_PRESETS", "ScheduleManager", "ScheduledTask", "generate_schedule_id", "get_schedule_manager", "next_run_time", "validate_cron_expression"]`. All `__all__` entries are isort-sorted per RUF022. **3809 passing tests (+48 new: 25 AI providers, 6 pr_description, 7 model_provider, 10 schedules), 98 skipped.**

## Mar 13 (cont.) — Task cancellation / kill signal from UI (v160)

**Feature:** Implemented the TODO.md item "kill signal from UI for a task." Added `TaskCancelResponse` Pydantic model and `POST /tasks/{task_id}/cancel` endpoint to `server/app.py`. The `_cancel_task()` helper validates task_id (non-empty, strips whitespace), checks if the task is already in a terminal state (`SUCCESS`/`FAILURE`/`REVOKED`), and calls `celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")` for running/queued tasks. Added cancel button to the inline HTML monitor page with red styling and JS `cancelTask()` function with confirm dialog. Added cancel button to the React frontend `App.tsx` monitor bar, conditionally rendered for non-terminal tasks using existing `isTerminalTaskStatus()`. The frontend already handled `REVOKED` status in `statusTone()` and `isTerminalTaskStatus()`. **4367 passing tests (+15 new: 2 model, 5 helper, 5 endpoint, 3 HTML monitor), 2 skipped. Frontend: 178 passing.**

## Mar 14 — Complete `__all__` exports across all remaining modules (v161)

**API consistency:** Added `__all__` declarations to 13 remaining modules, completing project-wide explicit public API coverage. Hand modules: `base.py` (`["Hand", "HandResponse"]`), `e2e.py` (`["E2EHand"]`), `iterative.py` (`["BasicAtomicHand", "BasicLangGraphHand"]`). CLI hand modules: `claude.py` (`["ClaudeCodeHand"]`), `codex.py` (`["CodexCLIHand"]`), `gemini.py` (`["GeminiCLIHand"]`), `goose.py` (`["GooseCLIHand"]`), `opencode.py` (`["OpenCodeCLIHand"]`), `docker_sandbox_claude.py` (`["DockerSandboxClaudeCodeHand"]`). Server modules: `app.py` (17 public symbols: app instance + 16 Pydantic models), `celery_app.py` (`["build_feature", "celery_app"]`), `mcp_server.py` (`["main", "mcp"]`). CLI entry: `main.py` (`["build_parser", "main"]`). All entries isort-sorted per RUF022. **3858 passing tests (+48 new: 35 passed, 13 skipped without server extras), 112 skipped.**

## Mar 14 (cont.) — Extract bootstrap doc constants, DRY backend names, add docstrings (v162)

**Maintainability and documentation:** Extracted inline bootstrap document filename tuples to module-level constants (`_README_CANDIDATES = ("README.md", "readme.md")`, `_AGENT_DOC_CANDIDATES = ("AGENT.md", "agent.md")`) in `iterative.py`, replacing inline tuples in `_build_bootstrap_context()`. Extracted hardcoded backend name strings to class-level `_BACKEND_NAME` constants in `BasicLangGraphHand` (`"basic-langgraph"`) and `BasicAtomicHand` (`"basic-atomic"`), replacing 6 hardcoded occurrences across `run()` and `stream()` methods. Added Google-style docstrings with Args/Returns sections to 8 key protected methods in `_BasicIterativeHand`: `_execution_tools_enabled()`, `_web_tools_enabled()`, `_tool_instructions()`, `_format_command()`, `_tool_disabled_error()`, `_read_bootstrap_doc()`, `_build_tree_snapshot()`, `_build_bootstrap_context()`. **3880 passing tests (+22 new), 112 skipped.**

## Mar 14 (cont.) — Hand base.py docstrings, Claude CLI stream-json constants (v163)

**Documentation and maintainability:** Added Google-style docstrings with Args/Returns/Raises sections to 9 protected methods in `base.py`: `_is_interrupted()`, `_default_base_branch()`, `_run_git_read()`, `_github_repo_from_origin()`, `_build_generic_pr_body()`, `_configure_authenticated_push_remote()`, `_should_run_precommit_before_pr()`, `_run_precommit_checks_and_fixes()`, `_finalize_repo_pr()`. Extracted 6 hardcoded stream-json event/block type strings to module-level constants in `claude.py`: `_EVENT_TYPE_ASSISTANT`, `_EVENT_TYPE_USER`, `_EVENT_TYPE_RESULT`, `_BLOCK_TYPE_TOOL_USE`, `_BLOCK_TYPE_TOOL_RESULT`, `_BLOCK_TYPE_TEXT`. **3902 passing tests (+22 new), 112 skipped.**

## Mar 14 (cont.) — Close remaining coverage gaps in Hand base.py, pr_description.py, claude.py (v164)

**Test coverage:** Closed 10 previously uncovered lines across 3 modules with 8 new targeted tests. Hand base.py: tested `pr_number is None` ValueError guards on `_push_to_existing_pr`, `_update_pr_description`, `_create_pr_for_diverged_branch` (3 tests). pr_description.py: tested multi-word keyword substring matching in `_infer_commit_type` ("clean up" → refactor, "github action" → ci), second `FileNotFoundError` in `_get_uncommitted_diff` (git add succeeds but git diff --cached fails), and empty-line skip in `_commit_message_from_prompt` boilerplate extraction (4 tests). claude.py: tested `_resolve_cli_model()` empty-model early return by monkeypatching `_DEFAULT_MODEL` to "" (1 test). **3910 passing tests (+8 new), 112 skipped.**

## Mar 14 (cont.) — Extract command exit code constants, DRY boolean env parsing, add CLI hand docstrings (v165)

**Maintainability and documentation:** Extracted 3 magic Unix exit codes to module-level constants in `command.py` (`_EXIT_CODE_TIMEOUT = 124`, `_EXIT_CODE_NOT_FOUND = 127`, `_EXIT_CODE_CANNOT_EXECUTE = 126`). DRYed boolean env var parsing by introducing `_TRUTHY_VALUES` frozenset and `_is_truthy_env()` helper in `config.py`, replacing 4 inline `("1", "true", "yes")` tuples in `from_env()` and 1 in `e2e.py` `_draft_pr_enabled()`. Added Google-style docstrings with Args/Returns sections to 7 methods in `cli/base.py`: 3 public (`run`, `stream`, `interrupt`) and 4 protected template methods (`_command_not_found_message`, `_fallback_command_when_not_found`, `_retry_command_after_failure`, `_no_change_error_after_retries`). **3944 passing tests (+34 new), 112 skipped.**

## Mar 14 (cont.) — Consolidate `_FAILURE_OUTPUT_TAIL_LENGTH`, harmonize `_is_truthy`, add CLI hand docstrings (v166)

**Maintainability and DRY:** Consolidated `_FAILURE_OUTPUT_TAIL_LENGTH = 2000` from 4 CLI hand subclass files (claude.py, codex.py, gemini.py, opencode.py) to `cli/base.py` — all subclasses now import from the shared base. Created `_CLI_TRUTHY_VALUES = _TRUTHY_VALUES | {"on"}` in `cli/base.py` to harmonize `_is_truthy()` with config's `_TRUTHY_VALUES`, establishing a single source of truth. Added Google-style docstrings with Args/Returns sections to 12 methods in `codex.py` and 14 methods in `gemini.py`. **3986 passing tests (+42 new), 112 skipped.**

## Mar 15 — Add docstrings to goose.py/opencode.py/e2e.py, extract E2E and OpenCode constants (v167)

**Documentation and constant extraction:** Added Google-style docstrings with Args/Returns/Raises sections to 13 methods in `goose.py`, 5 methods in `opencode.py`, and 8 methods in `e2e.py`. Extracted 5 hardcoded auth error token strings to `_AUTH_ERROR_TOKENS` tuple constant in `opencode.py`. Extracted 5 hardcoded E2E strings to module-level constants in `e2e.py`: `_E2E_GIT_USER_NAME`, `_E2E_GIT_USER_EMAIL`, `_E2E_COMMIT_MESSAGE`, `_E2E_PR_TITLE`, `_E2E_STATUS_MARKER`. **4030 passing tests (+29 new), 112 skipped.**

## Mar 15 (cont.) — Add docstrings to langgraph.py, app.py validators, cli/base.py (v168)

**Documentation:** Added Google-style docstrings with Args/Returns/Raises sections to 3 methods in `langgraph.py` (`__init__`, `_build_agent`, `run`), 4 validator methods in `server/app.py` `_ToolSkillValidatorMixin` (`_coerce_tools`, `_validate_tools`, `_coerce_skills`, `_validate_skills`), and 22 methods in `cli/base.py` covering initialization, command resolution, container execution, timing, prompt building, retry logic, and finalization helpers. **4113 passing tests (+83 new), 126 skipped.**

## Mar 15 (cont.) — Add docstrings to iterative.py helper methods (v169)

**Documentation:** Added Google-style docstrings with Args/Returns/Raises sections to 21 methods across `iterative.py`: 18 in `_BasicIterativeHand`, 1 in `BasicLangGraphHand` (`_result_content`), and 2 in `BasicAtomicHand` (`_make_input`, `_extract_message`). **4173 passing tests (+60 new), 126 skipped.**

## Mar 15 (cont.) — Add Attributes sections to public dataclass docstrings (v170)

**Documentation:** Expanded one-line class docstrings on 12 public dataclasses to include Google-style `Attributes:` sections documenting each field. Covers `ToolSpec`/`ToolCategory` (registry.py), `WebSearchItem`/`WebSearchResult`/`WebBrowseResult` (web.py), `CommandResult` (command.py), `HandResponse` (base.py), `PRResult` (github.py), `PRDescription` (pr_description.py), `HandModel` (model_provider.py), `SkillSpec` (skills/__init__.py), `RepoIndex` (repo.py), `ScheduledTask` (schedules.py). **4197 passing tests (+24 new), 128 skipped.**

## Mar 15 (cont.) — Add Attributes to Config, docstrings to web.py and registry.py helpers (v171)

**Documentation:** Added Google-style `Attributes:` section to `Config` dataclass in `config.py` documenting all 11 fields (missed in v170's dataclass sweep). Added Google-style docstrings with Args/Returns/Raises sections to 4 private helpers in `web.py` (`_require_http_url`, `_strip_html`, `_as_string_keyed_dict`, `_extract_related_topics`) and 8 private helpers in `registry.py` (`_parse_str_list`, `_parse_positive_int`, `_parse_optional_str`, `_run_python_code`, `_run_python_script`, `_run_bash_script`, `_run_web_search`, `_run_web_browse`). **4233 passing tests (+36 new), 128 skipped.**

## Mar 15 (cont.) — Close reference-repo coverage gaps (v172)

**Coverage gap closure:** Closed 7 uncovered lines across 4 non-server modules: `_clone_reference_repos` invalid spec skip, timeout skip, successful clone in `cli/main.py`; `Config.from_env` non-str/non-list/tuple `reference_repos` fallback in `config.py`; `Hand._build_reference_repos_prompt_section` PermissionError in `hand/base.py`; `_run_bash_script` both-None/both-provided validation in `registry.py`. **4251 passing tests (+18 new), 128 skipped.**

## Mar 15 (cont.) — Close remaining non-server branch partials (v173)

**Coverage gap closure:** Closed 3 of 4 remaining branch partials in non-server modules. `iterative.py` empty-delta branches in AssertionError sync fallback (1137→1139) and awaitable non-iterable result (1163→1165). `e2e.py` line 291 `final_pr_number is None` defensive guard after `create_pr`. `pr_description.py` 581→583 confirmed unreachable (candidate always empty on first non-boilerplate line). Added 10 new tests including boilerplate-then-content extraction verification. **4261 passing tests (+10 new), 128 skipped.**

## Mar 15 (cont.) — Extract parser marker constants, DRY commit type regex, add docstrings (v174)

**Maintainability and documentation:** Extracted 3 parser marker constants in `pr_description.py` (`_PR_TITLE_MARKER`, `_PR_BODY_MARKER`, `_COMMIT_MSG_MARKER`) replacing 6 hardcoded occurrences. DRYed commit type prefix regex to `_COMMIT_TYPE_PREFIX_RE` constant replacing duplicate inline patterns. Extracted `_AUTH_FAILURE_SUBSTRINGS` tuple constant in `docker_sandbox_claude.py`. Added Google-style docstrings to 4 methods in `docker_sandbox_claude.py` and 4 methods in `cli/main.py`. **4306 passing tests (+45 new), 128 skipped.**

## Mar 15 (cont.) — Add docstrings to command.py helpers, docker_sandbox_claude.py methods, github.py dunders (v175)

**Documentation:** Added Google-style docstrings with Args/Returns/Raises sections to 4 private helpers in `command.py` (`_normalize_args`, `_resolve_cwd`, `_resolve_python_command`, `_run_command`), 4 methods in `docker_sandbox_claude.py` (`__init__`, `_should_cleanup`, `_execution_mode`, `_fallback_command_when_not_found`), and 3 dunder methods in `github.py` (`__post_init__`, `__enter__`, `__exit__`). **4326 passing tests (+20 new), 128 skipped.**

## Mar 15 (cont.) — Add docstrings to AI providers, github.py public methods, Hand base.py methods (v176)

**Documentation:** Added Google-style docstrings with Args/Returns/Raises sections to 10 AI provider methods (`_build_inner` and `_complete_impl` in all 5 providers: `AnthropicProvider`, `OpenAIProvider`, `GoogleProvider`, `LiteLLMProvider`, `OllamaProvider`), 4 `github.py` public methods (`whoami`, `get_pr`, `default_branch`, `update_pr_body` — expanded from one-liners to full Google-style with Args/Returns/Raises), and 7 `Hand` base.py methods (`__init__`, `_build_system_prompt`, `_build_reference_repos_prompt_section`, `interrupt`, `reset_interrupt`, `_use_native_git_auth_for_push`, `_push_noninteractive`). **4387 passing tests (+61 new), 128 skipped.**

## Mar 15 (cont.) — Add `__all__` exports to langgraph.py/atomic.py/cli/base.py, add docstrings (v177)

**Documentation and API consistency:** Added `__all__` exports to 3 remaining hand modules missing them (`langgraph.py`, `atomic.py`, `cli/base.py`). Added Google-style docstrings to 4 undocumented methods: `AtomicHand.__init__`, `AtomicHand.run`, `AtomicHand.stream`, `LangGraphHand.stream`. **4415 passing tests (+28 new), 128 skipped.**

## Mar 15 (cont.) — Extract GitHub URL constants, DRY Ollama base URL, namespace `__all__` (v178)

**Maintainability and DRY:** Extracted `_GITHUB_TOKEN_USER = "x-access-token"` constant in 4 modules (`github.py`, `base.py`, `cli/main.py`, `celery_app.py`) replacing 4 hardcoded clone URL occurrences and 1 in token redaction regex. Extracted `_GITHUB_HOSTNAME = "github.com"` in `base.py` replacing 3 hardcoded occurrences in hostname check, SCP regex, and push URL. Extracted `_DEFAULT_OLLAMA_BASE_URL` and `_DEFAULT_OLLAMA_API_KEY` in `model_provider.py`. Added `__all__: list[str] = []` to 4 namespace `__init__.py` files (`lib/`, `lib/hands/`, `server/`, `cli/`) completing project-wide explicit `__all__` coverage. **4443 passing tests (+27 new), 130 skipped.**

## Mar 15 (cont.) — DRY GitHub URL helpers, consolidate server constants (v179)

**Maintainability and DRY:** Created `lib/github_url.py` shared module with `build_clone_url()`, `validate_repo_spec()`, `redact_credentials()`, `noninteractive_env()`, and `GITHUB_TOKEN_USER`/`GITHUB_HOSTNAME` constants — eliminating identical implementations in `cli/main.py` and `server/celery_app.py`. Updated `lib/github.py` and `lib/hands/v1/hand/base.py` to import `_GITHUB_TOKEN_USER`/`_GITHUB_HOSTNAME` from the shared module. Created `server/constants.py` consolidating Anthropic usage API (`ANTHROPIC_USAGE_URL`, `ANTHROPIC_BETA_HEADER`, `USAGE_USER_AGENT`) and Keychain (`KEYCHAIN_SERVICE_NAME`, `KEYCHAIN_OAUTH_KEY`, `KEYCHAIN_ACCESS_TOKEN_KEY`, `JWT_TOKEN_PREFIX`) constants — replacing duplicates between `server/app.py` and `server/celery_app.py`. **4474 passing tests (+33 new: 20 github_url, 8 server constants, 5 consumer consistency), 131 skipped.**

## Mar 15 (cont.) — Add docstrings to celery_app.py progress-tracking helpers (v180)

**Documentation:** Added Google-style docstrings with Args/Returns sections to 4 undocumented standalone functions (`_trim_updates`, `_append_update`, `_update_progress`, `_setup_periodic_tasks`) and 3 undocumented `_UpdateCollector` methods (`__init__`, `feed`, `flush`) in `server/celery_app.py`. These were the last remaining undocumented functions in the server module. **4476 passing tests (+14 new, skipped without celery), 131 skipped.**

## Mar 15 (cont.) — Add docstrings to last 4 undocumented functions, consolidate daily files (v181)

**Documentation and cleanup:** Added Google-style docstrings with Args/Returns/Raises sections to the last 4 undocumented functions in the codebase: `_wrap_container_if_enabled()` in `cli/base.py`, `_check_redis_health()`, `_check_db_health()`, and `_check_workers_health()` in `server/app.py`. This completes project-wide docstring coverage — every function/method now has a Google-style docstring. Consolidated redundant daily plan files (2026-03-11 through 2026-03-14) into weekly files (Week-11, Week-12), updating PLANS.md links accordingly. **4482 passing tests (+6 new: 6 passed, 10 skipped without server extras), 140 skipped.**

## Mar 15 (cont.) — Extract pre-commit error constant, DRY git error fallback, task state guards (v182)

**Maintainability and correctness:** Extracted `_PRECOMMIT_UV_MISSING_MSG` constant in `base.py`, replacing 2 identical multi-line error message strings in `_run_precommit_checks_and_fixes()` first-pass and second-pass `FileNotFoundError` handlers. Extracted `_DEFAULT_GIT_ERROR_MSG = "unknown git error"` constant for the `stderr.strip() or ...` fallback in `_configure_authenticated_push_remote()`. Added 2 module-level assertions in `server/app.py` verifying that `_TERMINAL_TASK_STATES` and `_CURRENT_TASK_STATES` are disjoint, and that `_TASK_STATE_PRIORITY` keys are a subset of `_CURRENT_TASK_STATES`. Consolidated redundant `2026-03-15.md` daily plan file into `Week-12.md`, updated PLANS.md links. **4493 passing tests (+11 new: 11 passed, 8 skipped without fastapi), 148 skipped.**

## Mar 15 (cont.) — DRY commit/PR message templates, add debug logging to silent handlers (v183)

**Maintainability and debuggability:** Extracted `_DEFAULT_COMMIT_MSG_TEMPLATE` and `_DEFAULT_PR_TITLE_TEMPLATE` f-string template constants in `base.py`, replacing 4 duplicated inline f-strings across `_push_to_existing_pr`, `_create_pr_for_diverged_branch`, and `_finalize_repo_pr`. Both use `{backend}` placeholder and `.format(backend=...)` at call sites. Added `logger.debug(..., exc_info=True)` calls to 2 previously-silent `except Exception` handlers in `server/app.py`: `_safe_inspect_call()` (logs failed method name) and `_collect_celery_current_tasks()` (logs inspect init failure). **4510 passing tests (+17 new: 12 passed, 5 skipped without fastapi), 153 skipped.**

## Mar 15 (cont.) — AI provider empty message validation, mkdir_path hardening, content type check (v184)

**Consistency and validation:** Lifted empty-message validation from `GoogleProvider._complete_impl()` to `AIProvider.complete()` base class — all 5 providers now consistently reject messages where all content is empty before reaching the provider-specific implementation. Removed the redundant check from `GoogleProvider._complete_impl()`. Added `OSError` handling to `mkdir_path()` in `filesystem.py` — raw `OSError` (permission denied, disk full) is now wrapped in `RuntimeError` with path context, matching the existing pattern in `write_text_file()`. Added content type validation to `normalize_messages()` — non-string, non-None `content` values (int, list, dict, bool, float) now raise `TypeError` instead of being silently converted via `str()`. Updated existing Google-specific empty-message tests to test via `complete()` instead of `_complete_impl()`. Fixed `completed_plan_paths` test fixtures to use `rglob` for weekly consolidation files in subdirectories, and added `_is_summary_file()` filter to skip weekly summary files in versioned plan structure tests. Removed redundant `2026-03-15.md` daily plan file. **4527 passing tests (+17 new), 153 skipped.**

## Mar 15 (cont.) — API key whitespace stripping, PR body validation, filesystem error messages (v185)

**Defensive coding:** Added `.strip()` to API key environment variable reads across all 5 AI providers (OpenAI, Anthropic, Google, LiteLLM, Ollama) — prevents silent auth failures from copy-paste whitespace. Added `.strip()` with fallback defaults to Ollama provider (`api_key` and `base_url`). Added `commit_sha` and `stamp_utc` validation to `_build_generic_pr_body()` — empty/whitespace/non-string values now raise `ValueError`. Included display path in `read_text_file()` `FileNotFoundError` and `IsADirectoryError` messages for better debugging. **4547 passing tests (+20 new), 153 skipped.**

## Mar 15 (cont.) — Claude CLI docstrings, MCP tool input validation (v186)

**Docstrings and validation:** Added Google-style docstrings to 5 undocumented methods in `claude.py`: `_StreamJsonEmitter.__call__` (buffer and line processing), `_StreamJsonEmitter._process_line` (JSON event parsing with 3 event types), `_StreamJsonEmitter.result_text` (result priority with fallback), `ClaudeCodeHand._resolve_cli_model` (GPT model filtering), `ClaudeCodeHand._skip_permissions_enabled` (env var + root check logic). Added empty/whitespace `ValueError` validation to MCP `path_exists` tool (previously the only path-based MCP tool without path validation). Added mutual-exclusivity validation to MCP `run_bash_script` — rejects both-None and both-provided `script_path`/`inline_script` at the MCP layer instead of deferring to downstream code. Added full Google-style docstrings to both MCP tools. **4577 passing tests (+30 new), 153 skipped.**

## Mar 15 (cont.) — Server endpoint path parameter validation (v187)

**Validation:** Added empty/whitespace validation to 8 FastAPI endpoint path parameters (`task_id` in `monitor`/`get_task`, `schedule_id` in 6 schedule endpoints). Extracted `_validate_path_param()` shared helper following the existing `_cancel_task()` validation pattern. Added Google-style docstrings to `_build_task_status()` and `_schedule_to_response()`. Refactored `_cancel_task()` to use `_validate_path_param()` (DRY). **4615 passing tests (+38 new, 2 skipped).**

## Mar 15 (cont.) — DRY redact_credentials, constant-based regex, debug logging (v188)

**Maintainability and debuggability:** Fixed `redact_credentials()` in `github_url.py` to use `GITHUB_TOKEN_USER` and `GITHUB_HOSTNAME` constants in regex pattern instead of hardcoded strings (consistency with `build_clone_url()` which already uses these constants). DRYed `_redact_sensitive()` in `github.py` to delegate to `redact_credentials()` from the shared module, eliminating a duplicate regex implementation and removing the unused `import re` from `github.py`. Added `logger.debug(..., exc_info=True)` to 2 remaining catch-all exception handlers without traceback logging: `_finalize_repo_pr()` in `base.py` and `_ci_fix_loop()` in `cli/base.py` — all catch-all handlers in lib/ now consistently log debug tracebacks. **4588 passing tests (+11 new), 154 skipped.**

## Mar 15 (cont.) — Input validation for PR description/commit message and CLI max-iterations (v189)

**Input validation:** Added `base_branch` and `backend` empty/whitespace validation to `generate_pr_description()` in `pr_description.py` — rejects empty, whitespace-only, and tab-only values with `ValueError` before reaching git diff or prompt building. Added `backend` empty/whitespace validation to `generate_commit_message()` (same pattern). Added `--max-iterations` positive integer validation to `cli/main.py`, matching the existing `--pr-number` validation pattern (exits with code 1 and error message for zero/negative values). **4603 passing tests (+15 new: 8 PR description validation, 4 commit message backend validation, 4 CLI max-iterations validation), 154 skipped.**

## Mar 15 (cont.) — Pre-compile regex constants, DRY function-local imports (v190)

**Performance and DRY:** Moved 4 function-local `import re` statements to module-level in `pr_description.py`, eliminating redundant per-call import overhead. Compiled `_COMMIT_TYPE_PREFIX_RE` from a raw string to `re.compile()` with `re.IGNORECASE` baked in, replacing 2 `re.sub()` call sites with `.sub()` on the compiled pattern. Extracted 2 new pre-compiled regex constants in `pr_description.py` (`_BRACKET_BANNER_RE`, `_NUMBERED_LIST_RE`) from inline `re.match()` patterns in `_is_boilerplate_line()`, which is called per-line during PR description generation. Extracted 4 pre-compiled regex constants in `web.py` (`_SCRIPT_STYLE_RE`, `_HTML_TAG_RE`, `_HORIZONTAL_WHITESPACE_RE`, `_BLANK_LINES_RE`) from inline `re.sub()` patterns in `_strip_html()`. Updated existing `_COMMIT_TYPE_PREFIX_RE` tests to verify compiled `re.Pattern` type and `IGNORECASE` flag. **4631 passing tests (+28 new: 2 compiled pattern type, 13 boilerplate regex, 13 HTML strip regex), 154 skipped.**

## Mar 15 (cont.) — _render_monitor_page tests, _extract_task_kwargs branches, non-string worker keys (v192)

**Test coverage expansion:** Added 21 new unit tests covering 3 previously untested or partially tested `server/app.py` functions. `_render_monitor_page` (15 tests: basic pending task with auto-refresh, terminal status no-refresh/no-cancel, prompt extraction from result dict, empty/whitespace/non-string prompt handling, updates list rendering, non-list updates fallback, None result defaults, HTML escaping of task_id/prompt/updates, FAILURE/REVOKED terminal handling, prompt whitespace stripping, mixed-type updates coercion, cancel button task_id reference). `_extract_task_kwargs` request branches (5 tests: request.kwargs invalid string fallback, empty string fallback, top-level kwargs priority, invalid top-level fallthrough to request dict, request kwargs Python literal parsing). `_iter_worker_task_entries` non-string keys (2 tests: int/None keys filtered, all non-string keys returns empty). Server/app.py coverage 88% → 89%, branch partials 17 → 13. **5358 passing tests (+21 new), 2 skipped.**

## Mar 15 (cont.) — Server app.py test coverage: pure functions, cancel, Flower, worker capacity (v191)

**Test coverage expansion:** Added 41 new unit tests in `tests/test_server_app_coverage.py` covering 8 previously untested `server/app.py` functions. `_validate_path_param` (5 tests: valid stripped, passthrough, empty/whitespace raises, error includes param name). `_redact_token` (6 tests: None, empty, short ≤8 chars, exactly 12, long, 13-char boundary). `_build_form_redirect_query` (5 tests: minimal fields, all flags, default ci_wait, false booleans excluded, whitespace-only tools excluded). `_build_task_status` (3 tests: ready task uses result, pending task uses info dict, unknown state returns None result). `_cancel_task` (7 tests: running revoke+SIGTERM, terminal SUCCESS/FAILURE/REVOKED skip revoke, pending task, empty/whitespace task_id raises). `_enqueue_build_task` (2 tests: basic enqueue returns BuildResponse, all fields forwarded). `_fetch_flower_current_tasks` (6 tests: no URL returns empty, HTTP error returns empty, non-dict payload returns empty, active tasks extracted, terminal states filtered, non-HH tasks filtered, non-dict entries skipped). `_resolve_worker_capacity` (6 tests: Celery stats, env var fallback, CELERY_CONCURRENCY env, empty dict, inspect exception fallback, missing pool key). Server app.py coverage jumped from 51% to 88%. **5336 passing tests (+41 new), 2 skipped.**

---

**Week summary:** Feature addition (per-task GitHub token override) flowing from CLI/server through Config to GitHubClient, dead code cleanup, constant docstring consistency, security fix removing hardcoded database credentials, input validation for GitHubClient branch/commit/identity methods, git subprocess timeout protection, clone URL format validation, error message redaction, comprehensive GitHubClient method input validation hardening, runtime type validation for filesystem/tool/skill/truncation functions, CI fix removing stale `ty: ignore` comments, push remote/precommit subprocess timeouts with input validation, PR description diff/clone subprocess timeouts with `read_text_file` max_chars validation, `read_text_file` max_file_size validation, Google provider KeyError defense, Config.from_env() whitespace stripping, module `__all__` exports across all 30 modules (completing project-wide explicit public API coverage), `normalize_messages()` Google-style docstring, PR body input validation, DuckDuckGo API URL constant extraction, `normalize_relative_path` empty-string validation, task cancellation (kill signal from UI) with `POST /tasks/{task_id}/cancel` endpoint and cancel buttons in both UIs, bootstrap doc filename constant extraction, DRY backend name constants, iterative hand docstrings, Hand base.py docstrings, Claude CLI stream-json event type constants, coverage gap closure (reference-repo and remaining branch partials), command exit code constants, DRY boolean env parsing, `_FAILURE_OUTPUT_TAIL_LENGTH` consolidation, `_is_truthy` harmonization, comprehensive CLI hand docstring coverage (codex/gemini/goose/opencode/langgraph), E2E constant extraction, auth error token constant extraction, app.py validator docstrings, cli/base.py method docstrings (29 methods), iterative.py helper docstrings (21 methods), Google-style Attributes sections on all 13 public dataclasses, web.py/registry.py private helper docstrings, pr_description.py parser marker constant extraction and commit type regex DRY, docker_sandbox_claude.py auth failure constant extraction and docstrings, cli/main.py private method docstrings, command.py private helper docstrings, docker_sandbox_claude.py remaining method docstrings, github.py dunder method docstrings, AI provider `_build_inner`/`_complete_impl` docstrings (all 5 providers), github.py public method docstring expansion (`whoami`/`get_pr`/`default_branch`/`update_pr_body`), Hand base.py method docstrings (`__init__`/`_build_system_prompt`/`_build_reference_repos_prompt_section`/`interrupt`/`reset_interrupt`/`_use_native_git_auth_for_push`/`_push_noninteractive`), `__all__` exports to langgraph/atomic/cli base modules, GitHub URL constant extraction (`_GITHUB_TOKEN_USER`/`_GITHUB_HOSTNAME` across 4 modules), Ollama base URL DRY (`_DEFAULT_OLLAMA_BASE_URL`/`_DEFAULT_OLLAMA_API_KEY`), namespace `__init__.py` `__all__` completion, celery_app.py progress-tracking helper docstrings, completing project-wide docstring coverage with last 4 undocumented functions (cli/base.py `_wrap_container_if_enabled`, app.py health check helpers), daily plan file consolidation. Grew from 3542 to 4482 backend tests.
