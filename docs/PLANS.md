# Plans

Index of execution plans for helping_hands development.

## Active plans

(none)

## Completed plans

- [2026-03-16 v216](exec-plans/completed/2026/v216-metadata-key-constants.md) —
  Extract 8 metadata key constants (`_META_PR_STATUS`, `_META_PR_URL`,
  `_META_PR_NUMBER`, `_META_PR_BRANCH`, `_META_PR_COMMIT`,
  `_META_CI_FIX_STATUS`, `_META_CI_FIX_ATTEMPTS`, `_META_CI_FIX_ERROR`)
  to `base.py`, replacing 72 bare string literals across 6 hand modules;
  28 tests (value, type, uniqueness, AST-based source consistency checks);
  5216 passed, 219 skipped

- [2026-03-15 v215](exec-plans/completed/2026/v215-schedule-endpoint-tests.md) —
  Server schedule endpoint 34 tests: `_get_schedule_manager`, all 8
  schedule CRUD/trigger endpoints, `/notif-sw.js`, `/config`, `/build`,
  `/build/form` ValidationError redirect, `_is_running_in_docker`;
  server/app.py coverage 89% → 99%; 6112 passed, 2 skipped

- [2026-03-15 v214](exec-plans/completed/2026/v214-schedule-manager-tests.md) —
  ScheduleManager unit tests with mocked Redis/Celery/RedBeat (50 tests),
  schedules.py coverage 0% → 97%; 6078 passed, 2 skipped

- [2026-03-15 v213](exec-plans/completed/2026/v213-from-dict-validation-coverage-threshold-package-exports.md) —
  `ScheduledTask.from_dict` empty/whitespace required-field rejection,
  `validate_cron_expression` whitespace stripping, `fail_under = 75` coverage
  threshold, package-level `__all__` exports for lib/server/cli; 28 tests
  (5189 passed, 217 skipped)

- [2026-03-15 v212](exec-plans/completed/2026/v212-dry-run-status-truncation-auth-presence.md) —
  DRY `_RUN_STATUS_*` constants, `_TRUNCATION_MARKER`, `_AUTH_PRESENT_LABEL`/
  `_AUTH_ABSENT_LABEL` in iterative.py; 25 tests (5189 passed, 216 skipped)

- [2026-03-15 v211](exec-plans/completed/2026/Week-12.md) —
  DRY `_ENCODING_FALLBACK_CHAIN` in web.py, `_GIT_REF_PREFIX` and
  `_CHECK_RUN_STATUS_COMPLETED` in github.py; 21 tests (5164 passed, 216 skipped)

- [2026-03-15 v210](exec-plans/completed/2026/Week-12.md) —
  Extract `_GIT_HOOK_FAILURE_MARKERS` constant in base.py, dedicated unit tests
  for `validation.py` (21 tests) and `github_url.py` (33 tests), versioned
  contract tests (16 tests); 5143 passed, 216 skipped

- [2026-03-15 v209](exec-plans/completed/2026/Week-12.md) —
  `CIConclusion(StrEnum)`, `CIFixStatus(StrEnum)`, pre-lowercase boilerplate
  prefixes, `_LANGCHAIN_STREAM_EVENT` constant; 36 tests (5073 passed, 216 skipped)

- [2026-03-15 v208](exec-plans/completed/2026/Week-12.md) —
  `PRStatus(StrEnum)` with 12 members replacing 5 string constants + 7 ad-hoc
  strings, `_build_generic_pr_body` validation standardized to
  `require_non_empty_string`, DRY `_pr_result_metadata()` helper (3 sites);
  38 tests (5037 passed, 216 skipped)

- [2026-03-15 v207](exec-plans/completed/2026/Week-12.md) —
  DRY shared validation helpers (`require_non_empty_string`,
  `require_positive_int`) extracted to `validation.py`, applied across 9 files;
  36 tests (4999 passed, 216 skipped)

- [2026-03-15 v206](exec-plans/completed/2026/Week-12.md) --
  DRY payload validators (iterative.py `_parse_str_list`/`_parse_positive_int`/
  `_parse_optional_str` → registry.py delegation), shared
  `_normalize_and_deduplicate` helper for tool/skill selection normalization,
  shared `_raise_url_error` helper in web.py;
  30 tests (all new, 4967 passed, 212 skipped)

- [2026-03-15 v205](exec-plans/completed/2026/Week-12.md) --
  DRY `_validate_script_path()` in command.py (shared helper replacing duplicated
  5-line validation in `run_python_script`/`run_bash_script`), DRY `_display_path()`
  in filesystem.py (replacing 4× inline `target.relative_to(root).as_posix()`),
  DRY `self.install_hint` in 5 AI provider `_build_inner()` error messages, DRY
  `KEYCHAIN_TIMEOUT_S`/`USAGE_API_TIMEOUT_S` to `server/constants.py`;
  27 tests (23 new, 4 skipped without fastapi/celery)

- [2026-03-15 v204](exec-plans/completed/2026/Week-12.md) --
  Fix form default mismatch (`"codexcli"` → `_DEFAULT_BACKEND`), DRY inline
  truthy set → `_TRUTHY_VALUES`, move inline `import time` to top-level, DRY
  `3.0` → `_DEFAULT_CI_WAIT_MINUTES`, extract `_TOOL_SUMMARY_KEY_MAP`/
  `_TOOL_SUMMARY_STATIC` dispatch table in claude.py `_summarize_tool()`;
  52 tests (40 new, 12 skipped without fastapi)

- [2026-03-15 v203](exec-plans/completed/2026/Week-12.md) --
  DRY `_detect_auth_failure(output, extra_tokens)` helper in `cli/base.py`
  (encapsulates 3-line tail-extraction + token-check pattern from 4 subclasses,
  removes direct `_AUTH_ERROR_TOKENS`/`_FAILURE_OUTPUT_TAIL_LENGTH` imports),
  DRY `_truncate_with_ellipsis(text, limit)` (replaces 4× inline slicing in
  claude.py `_StreamJsonEmitter`); 50 tests (all new)

- [2026-03-15 v202](exec-plans/completed/2026/Week-12.md) --
  DRY `_DEFAULT_PYTHON_VERSION` in `mcp_server.py` (2× hardcoded `"3.13"` →
  import from `command.py`), DRY `_command_not_found_message` (enhance base
  class to include Docker rebuild hint via `command` parameter, remove 5
  redundant overrides from claude/codex/gemini/goose/opencode);
  39 tests (all new)

- [2026-03-15 v201](exec-plans/completed/2026/Week-12.md) --
  DRY Docker hint message templates: `_DOCKER_ENV_HINT_TEMPLATE` (4× auth
  failure messages in claude/codex/gemini/opencode) and
  `_DOCKER_REBUILD_HINT_TEMPLATE` (4× command-not-found messages in
  codex/gemini/goose/opencode) extracted to `cli/base.py`;
  24 tests (all new)

- [2026-03-15 v200](exec-plans/completed/2026/Week-12.md) --
  DRY timestamp helper (`_utc_stamp()` in base.py replacing 4× inline
  `datetime.now(UTC).replace(microsecond=0).isoformat()` in base.py/e2e.py),
  DRY celery truthy check (import `_TRUTHY_VALUES` from config.py in
  celery_app.py replacing inline tuple), DRY sandbox UUID hex length
  (`_SANDBOX_UUID_HEX_LENGTH` in docker_sandbox_claude.py now delegates to
  `_UUID_HEX_LENGTH` from base.py);
  4784 tests (19 new, 199 skipped)

- [2026-03-15 v199](exec-plans/completed/2026/Week-12.md) --
  DRY registry.py default constants: extract `_DEFAULT_PYTHON_VERSION` in
  command.py (replacing 2× hardcoded `"3.13"` in function defaults), extract
  `DEFAULT_SEARCH_MAX_RESULTS = 5` in web.py (added to `__all__`), import
  `_DEFAULT_SCRIPT_TIMEOUT_S` (3× `60`), `_DEFAULT_WEB_TIMEOUT_S` (2× `20`),
  `DEFAULT_SEARCH_MAX_RESULTS` (1× `5`), `_DEFAULT_PYTHON_VERSION` (2× `"3.13"`)
  in registry.py replacing 7 hardcoded literals in runner wrappers;
  5541 tests (17 new, 2 skipped)

- [2026-03-15 v198](exec-plans/completed/2026/Week-12.md) --
  DRY token redaction constants (`_REDACT_TOKEN_PREFIX_LEN`,
  `_REDACT_TOKEN_SUFFIX_LEN`, `_REDACT_TOKEN_MIN_PARTIAL_LEN` in app.py
  replacing 3× magic numbers in `_redact_token()`), use `_DEFAULT_CI_WAIT_MINUTES`
  constant in `_schedule_to_response` getattr fallback, root package `__all__`
  declaration, fix `_FakeScheduledTask` missing `github_token`/`reference_repos`
  fields with forwarding tests; 5524 tests (22 new, 2 skipped)

- [2026-03-15 v197](exec-plans/completed/2026/Week-12.md) --
  DRY field validation bound constants (`MAX_ITERATIONS_UPPER_BOUND`,
  `MIN_CI_WAIT_MINUTES`, `MAX_CI_WAIT_MINUTES`, `MAX_REPO_PATH_LENGTH`,
  `MAX_PROMPT_LENGTH`, `MAX_MODEL_LENGTH`, `MAX_GITHUB_TOKEN_LENGTH` in
  `server/constants.py` replacing 2× duplicated literals in BuildRequest and
  ScheduleRequest), `BackendName` type alias deduplication (moved above
  BuildRequest, added to `__all__`), `_BYTES_PER_MB` constant in filesystem.py;
  4736 tests (33 new, 192 skipped)


- [2026-03-15 v196](exec-plans/completed/2026/Week-12.md) --
  DRY shared defaults (`DEFAULT_BACKEND`, `DEFAULT_MAX_ITERATIONS`,
  `DEFAULT_CI_WAIT_MINUTES` in server/constants.py replacing 3× duplicated
  literals across app.py/schedules.py), `reference_repos` `max_length=10`
  validation in BuildRequest/ScheduleRequest, `USAGE_CACHE_TTL_S = 300` named
  constant replacing local `_USAGE_CACHE_TTL`; 4723 tests (27 new, 174 skipped)

- [2026-03-15 v195](exec-plans/completed/2026/Week-12.md) --
  DRY git identity (`_E2E_GIT_USER_NAME`/`_E2E_GIT_USER_EMAIL` in e2e.py now
  reference base.py shared constants), DRY browse max chars
  (`DEFAULT_BROWSE_MAX_CHARS = 12000` in web.py replacing 3× hardcoded `12000`
  across web.py/registry.py/mcp_server.py), DRY clone timeout
  (`GIT_CLONE_TIMEOUT_S = 120` in github_url.py replacing 2× duplicated constants
  in cli/main.py and celery_app.py); 4715 tests (15 new, 156 skipped)

- [2026-03-15 v194](exec-plans/completed/2026/Week-12.md) --
  DRY timeout constants (`_DEFAULT_SCRIPT_TIMEOUT_S` in command.py replacing 3× `60`,
  `_DEFAULT_WEB_TIMEOUT_S` in web.py replacing 2× `20`), PR status sentinel extraction
  (5 `_PR_STATUS_*` constants + 2 `_PR_STATUSES_*` frozensets in base.py replacing ~17
  scattered string literals across base.py/iterative.py/cli/base.py); 4700 tests (33 new,
  155 skipped)

- [2026-03-15 v193](exec-plans/completed/2026/Week-12.md) --
  DRY `_AUTH_ERROR_TOKENS` to `cli/base.py` (shared constant across claude/codex/gemini/opencode,
  eliminates 4× duplicated auth detection strings), Google-style docstrings for 4 iterative.py
  public methods (`BasicLangGraphHand.run`/`stream`, `BasicAtomicHand.run`/`stream`),
  frontend accessibility (aria-labels on inline form inputs, `.catch()` on 3 unhandled
  Notification/config promises); 4822 tests (37 new backend, 2 new frontend, 155 skipped)

- [2026-03-15 v192](exec-plans/completed/2026/Week-12.md) --
  `_render_monitor_page` test coverage (15 tests: pending/terminal rendering,
  prompt extraction, updates list, HTML escaping, cancel button), `_extract_task_kwargs`
  request.kwargs branch coverage (5 tests), `_iter_worker_task_entries` non-string
  key filtering (2 tests); server/app.py coverage 88% → 89%, branch partials 17 → 13;
  5358 tests (21 new, 2 skipped)

- [2026-03-15 v191](exec-plans/completed/2026/Week-12.md) --
  Server app.py test coverage: 41 new tests for 8 previously untested functions
  (`_validate_path_param`, `_redact_token`, `_build_form_redirect_query`,
  `_build_task_status`, `_cancel_task`, `_enqueue_build_task`,
  `_fetch_flower_current_tasks`, `_resolve_worker_capacity`); server/app.py
  coverage 51% → 88%; 5336 tests (41 new, 2 skipped)

- [2026-03-15 v190](exec-plans/completed/2026/Week-12.md) --
  Pre-compile regex constants: move `import re` to module-level in
  `pr_description.py` (DRY 4 function-local copies), compile
  `_COMMIT_TYPE_PREFIX_RE` to `re.compile()`, extract `_BRACKET_BANNER_RE`
  and `_NUMBERED_LIST_RE` in `pr_description.py`, extract 4 HTML strip
  regex constants in `web.py`; 4631 tests (28 new, 154 skipped)

- [2026-03-15 v189](exec-plans/completed/2026/Week-12.md) --
  Input validation for `generate_pr_description()` (`base_branch`, `backend`
  empty/whitespace rejection) and `generate_commit_message()` (`backend`
  validation), CLI `--max-iterations` positive integer validation;
  4603 tests (15 new, 154 skipped)

- [2026-03-15 v188](exec-plans/completed/2026/Week-12.md) --
  DRY `redact_credentials()` to use `GITHUB_TOKEN_USER`/`GITHUB_HOSTNAME` constants
  in regex, DRY `_redact_sensitive()` in github.py to delegate to shared module
  (removing unused `import re`), add `logger.debug(exc_info=True)` to 2 remaining
  catch-all exception handlers (`_finalize_repo_pr`, `_ci_fix_loop`); consolidate
  daily plan file; 4588 tests (11 new, 154 skipped)

- [2026-03-15 v187](exec-plans/completed/2026/Week-12.md) --
  Server endpoint path parameter validation: extract `_validate_path_param()` helper,
  add empty/whitespace validation to 8 FastAPI endpoints (`monitor`, `get_task`,
  6 schedule endpoints), refactor `_cancel_task()` to use shared helper, Google-style
  docstrings for `_build_task_status()` and `_schedule_to_response()`; 4615 tests
  (38 new, 2 skipped)

- [2026-03-15 v186](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to 5 claude.py methods (`__call__`, `_process_line`,
  `result_text`, `_resolve_cli_model`, `_skip_permissions_enabled`), add empty-path
  validation to MCP `path_exists`, add mutual-exclusivity validation to MCP
  `run_bash_script`; 4577 tests (30 new, 153 skipped)

- [2026-03-15 v185](exec-plans/completed/2026/Week-12.md) --
  Strip whitespace from API key env vars across all 5 AI providers (prevents silent
  auth failures), add `commit_sha`/`stamp_utc` validation to `_build_generic_pr_body()`,
  include path context in `read_text_file()` error messages; 4547 tests (20 new, 153 skipped)

- [2026-03-15 v184](exec-plans/completed/2026/Week-12.md) --
  Lift empty-message validation from Google provider to `AIProvider.complete()` base
  class, add OSError handling to `mkdir_path()`, add content type validation to
  `normalize_messages()`; 4527 tests (17 new, 153 skipped)

- [2026-03-15 v183](exec-plans/completed/2026/Week-12.md) --
  Extract `_DEFAULT_COMMIT_MSG_TEMPLATE` and `_DEFAULT_PR_TITLE_TEMPLATE`
  constants in base.py (DRY 4 duplicate f-strings), add `logger.debug` to 2
  silent exception handlers in server/app.py; 4510 tests (17 new, 5 skipped
  without fastapi)

- [2026-03-15 v182](exec-plans/completed/2026/Week-12.md) --
  Extract `_PRECOMMIT_UV_MISSING_MSG` and `_DEFAULT_GIT_ERROR_MSG` constants in
  base.py (DRY 2 duplicate error messages), add task state set
  disjointness/subset guards in server/app.py; consolidate daily plan file;
  4493 tests (11 new, 8 skipped without fastapi)

- [2026-03-15 v181](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to last 4 undocumented functions
  (`_wrap_container_if_enabled` in cli/base.py, `_check_redis_health`,
  `_check_db_health`, `_check_workers_health` in server/app.py), completing
  project-wide docstring coverage; consolidate daily plan files; 4482 tests
  (6 new, 10 skipped without server extras)


- [2026-03-15 v180](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to 4 undocumented functions (`_trim_updates`,
  `_append_update`, `_update_progress`, `_setup_periodic_tasks`) and 3
  `_UpdateCollector` methods in celery_app.py; 4476 tests (14 new, skipped
  without celery)

- [2026-03-15 v179](exec-plans/completed/2026/Week-12.md) --
  DRY GitHub URL helpers (`lib/github_url.py`) and server constants
  (`server/constants.py`): eliminate duplicated `_github_clone_url()`,
  `_validate_repo_spec()`, `_redact_sensitive()`, `_git_noninteractive_env()`,
  `_GITHUB_TOKEN_USER` across cli/main.py, celery_app.py, github.py, base.py;
  consolidate Anthropic usage API and Keychain constants between app.py and
  celery_app.py; 4474 tests (33 new, 1 skipped)

- [2026-03-15 v178](exec-plans/completed/2026/Week-12.md) --
  Extract `_GITHUB_TOKEN_USER` constant in 4 modules (github.py, base.py, cli/main.py, celery_app.py), `_GITHUB_HOSTNAME` in base.py, `_DEFAULT_OLLAMA_BASE_URL`/`_DEFAULT_OLLAMA_API_KEY` in model_provider.py, add `__all__` to 4 namespace `__init__.py` files; 4443 tests (27 new, 2 skipped)

- [2026-03-15 v177](exec-plans/completed/2026/Week-12.md) --
  Add `__all__` exports to langgraph.py/atomic.py/cli/base.py, add docstrings to AtomicHand.__init__/run/stream and LangGraphHand.stream; 4415 tests (28 new)


- [2026-03-15 v176](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to 10 AI provider methods (5 providers), 4 github.py public methods, 7 Hand base.py methods; 4387 tests (61 new)

- [2026-03-15 v175](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to 4 command.py private helpers, 4 docker_sandbox_claude.py methods, 3 github.py dunders; 4326 tests (20 new)

- [2026-03-15 v174](exec-plans/completed/2026/Week-12.md) --
  Extract parser marker constants (`_PR_TITLE_MARKER`, `_PR_BODY_MARKER`, `_COMMIT_MSG_MARKER`), DRY `_COMMIT_TYPE_PREFIX_RE` regex, extract `_AUTH_FAILURE_SUBSTRINGS` in docker_sandbox_claude.py, add docstrings to 8 methods across 3 modules; 4306 tests (45 new)


- [2026-03-15 v173](exec-plans/completed/2026/Week-12.md) --
  Close 3 remaining non-server branch partials: iterative.py empty-delta (2 partials), e2e.py final_pr_number None guard; pr_description.py 581→583 confirmed unreachable; 4261 tests (10 new)

- [2026-03-15 v172](exec-plans/completed/2026/Week-12.md) --
  Close 7 uncovered lines across 4 non-server modules: _clone_reference_repos (invalid spec, timeout, success), Config reference_repos type fallback, Hand PermissionError in reference repo rglob, _run_bash_script both-None validation; 4251 tests (18 new)

- [2026-03-15 v171](exec-plans/completed/2026/Week-12.md) --
  Add Attributes to Config dataclass (11 fields), add Google-style docstrings to 4 web.py and 8 registry.py private helpers; 4233 tests (36 new)

- [2026-03-15 v170](exec-plans/completed/2026/Week-12.md) --
  Add Google-style Attributes sections to 12 public dataclass docstrings across 10 modules; 4197 tests (24 new)

- [2026-03-15 v169](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to iterative.py: _BasicIterativeHand (18), BasicLangGraphHand (1), BasicAtomicHand (2); 4173 tests (60 new)

- [2026-03-15 v168](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to langgraph.py (3), app.py validators (4), cli/base.py (22); 4113 tests (83 new)

- [2026-03-15 v167](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to goose.py (13), opencode.py (5), e2e.py (8); extract `_AUTH_ERROR_TOKENS` in opencode.py, 5 E2E constants; 4030 tests (29 new)

- [2026-03-14 v166](exec-plans/completed/2026/Week-12.md) --
  Consolidate `_FAILURE_OUTPUT_TAIL_LENGTH` to cli/base.py (DRY 4 copies), harmonize `_is_truthy` with config `_TRUTHY_VALUES` via `_CLI_TRUTHY_VALUES`, add Google-style docstrings to codex.py (12) and gemini.py (14); 3986 tests (42 new)

- [2026-03-14 v165](exec-plans/completed/2026/Week-12.md) --
  Extract command exit code constants (124/127/126), DRY boolean env parsing (`_TRUTHY_VALUES`/`_is_truthy_env`), add Google-style docstrings to 7 CLI hand methods; 3944 tests (34 new)


- [2026-03-14 v164](exec-plans/completed/2026/Week-12.md) --
  Close 10 uncovered lines: Hand base.py pr_number None guards (3 tests), pr_description.py multi-word keywords + second FileNotFoundError + empty-line skip (4 tests), claude.py empty model guard (1 test); 3910 tests (8 new)

- [2026-03-14 v163](exec-plans/completed/2026/Week-12.md) --
  Add Google-style docstrings to 9 Hand base.py methods, extract 6 Claude CLI stream-json event type constants; 3902 tests (22 new)


- [2026-03-14 v162](exec-plans/completed/2026/Week-12.md) --
  Extract bootstrap doc constants (`_README_CANDIDATES`, `_AGENT_DOC_CANDIDATES`), DRY backend name class constants (`_BACKEND_NAME`), add Google-style docstrings to 8 key methods in iterative.py; 3880 tests (22 new)

- [2026-03-14 v161](exec-plans/completed/2026/Week-12.md) --
  Add `__all__` exports to 13 remaining modules: hand base/e2e/iterative, 6 CLI hands (claude/codex/gemini/goose/opencode/docker_sandbox_claude), server app/celery/mcp, CLI main; 3858 tests (48 new: 35 passed, 13 skipped without server extras)

- [2026-03-13 v160](exec-plans/completed/2026/Week-12.md) --
  Task cancellation (kill signal from UI): `POST /tasks/{task_id}/cancel` endpoint, cancel button in inline HTML + React frontend, Celery `revoke(terminate=True)`; 4367 tests (15 new)

- [2026-03-13 v159](exec-plans/completed/2026/Week-12.md) --
  Add `__all__` to 8 modules: 5 AI providers (openai, anthropic, google, litellm, ollama), pr_description, model_provider, schedules; 3809 tests (48 new: 38 passed, 10 skipped)

- [2026-03-13 v158](exec-plans/completed/2026/Week-12.md) --
  Add `__all__` to web.py/repo.py/default_prompts.py/task_result.py, extract `_DUCKDUCKGO_API_URL` in web.py, `normalize_relative_path` empty-string validation; 3772 tests (29 new)

- [2026-03-13 v157](exec-plans/completed/2026/Week-12.md) --
  Add `__all__` exports to types.py, github.py, filesystem.py, command.py; enhance `normalize_messages()` docstring to Google-style with Args/Returns/Raises; 3743 tests (27 new)


- [2026-03-13 v156](exec-plans/completed/2026/Week-12.md) --
  Config.from_env() whitespace stripping (`repo`/`model`/`github_token`), `__all__` export in config.py, `_build_generic_pr_body` input validation, `_is_git_hook_failure` edge case tests; 3716 tests (16 new)

- [2026-03-13 v155](exec-plans/completed/2026/Week-12.md) --
  Input validation and defensive coding: `read_text_file()` `max_file_size` positive validation, Google provider `_complete_impl()` KeyError defense, `_get_diff()` fallback test coverage; 3700 tests (14 new)

- [2026-03-13 v154](exec-plans/completed/2026/Week-12.md) --
  Git subprocess timeouts for `pr_description.py` diff/add calls, `cli/main.py` and `celery_app.py` clone calls, `read_text_file()` `max_chars` positive validation; 3687 tests (21 new)

- [2026-03-13 v153](exec-plans/completed/2026/Week-12.md) --
  Subprocess timeouts for `_configure_authenticated_push_remote()` and `_run_precommit_checks_and_fixes()`, input validation for `_configure_authenticated_push_remote()` repo/token params and `GitHubClient.clone()` full_name; 3666 tests (16 new)


- [2026-03-13 v152](exec-plans/completed/2026/Week-12.md) --
  Remove 7 stale `ty: ignore` comments causing CI `unused-ignore-comment` warnings (model_provider.py, celery_app.py, schedules.py); 3649 tests (5 new regression guards)

- [2026-03-13 v151](exec-plans/completed/2026/Week-12.md) --
  Input type validation: `normalize_relative_path` non-string TypeError, `normalize_tool_selection`/`normalize_skill_selection` dict/set/int rejection, `_truncate_summary` positive limit guard; 3644 tests (28 new)

- [2026-03-13 v150](exec-plans/completed/2026/Week-12.md) --
  GitHubClient method input validation hardening: `create_pr()` title/head/base, `list_prs()` `_VALID_PR_STATES` enum, `get_check_runs()` ref, `upsert_pr_comment()` number/body; 3619 tests (20 new)

- [2026-03-13 v149](exec-plans/completed/2026/Week-12.md) --
  Git subprocess timeouts (`_run_git_read`, `_repo_has_changes`), clone URL `_validate_repo_spec()`, error message redaction; 3599 tests (17 new)

- [2026-03-13 v148](exec-plans/completed/2026/Week-12.md) --
  Remove hardcoded DB credentials in `_get_db_url_writer()` (security fix), GitHubClient branch/commit input validation (`_validate_branch_name`, empty message/name/email guards); 3582 tests (19 new)

- [2026-03-13 v147](exec-plans/completed/2026/Week-12.md) --
  Per-task GitHub token override (Config → CLI → server → Celery → GitHubClient), dead code removal, constant docstrings; 3563 tests (21 new)

- [2026-03-12 v146](exec-plans/completed/2026/Week-11.md) --
  Commit message quality: `_truncate_text()` truncation indicators for prompt/summary context, `_infer_commit_type()` smart type inference replacing hardcoded `"feat:"` prefix; 3542 tests (48 new)

- [2026-03-12 v145](exec-plans/completed/2026/Week-11.md) --
  Extract keychain constants (`_KEYCHAIN_SERVICE_NAME`, `_KEYCHAIN_OAUTH_KEY`, `_KEYCHAIN_ACCESS_TOKEN_KEY`) in app.py and celery_app.py, utilization numeric type guard, decode safety with `errors="replace"`; 3494 tests (20 new)

- [2026-03-12 v144](exec-plans/completed/2026/Week-11.md) --
  MCP index file limit constant (`_INDEX_FILES_LIMIT`), JWT token prefix constant (`_JWT_TOKEN_PREFIX`) in app.py and celery_app.py, E2E UUID hex length reuse from base.py; 3494 tests (15 new)

- [2026-03-12 v143](exec-plans/completed/2026/Week-11.md) --
  Redis write/delete/list error handling in schedules.py (`_save_meta`, `_delete_meta`, `_list_meta_keys`), extract `_SCHEDULE_ID_HEX_LENGTH` in schedules.py, extract `_OLLAMA_DEFAULT_HOST` in goose.py; 3487 tests (7 new)

- [2026-03-12 v142](exec-plans/completed/2026/Week-11.md) --
  Extract remaining magic numbers (`_HTTP_ERROR_BODY_PREVIEW_LENGTH`, `_USAGE_DATA_PREVIEW_LENGTH` in server/app.py, `_HOOK_ERROR_TRUNCATION_LIMIT`, `_GIT_REF_DISPLAY_LENGTH` in cli/base.py, `_SANDBOX_NAME_MAX_LENGTH`, `_SANDBOX_UUID_HEX_LENGTH` in docker_sandbox_claude.py), RepoIndex PermissionError handling in repo.py; 3480 tests (26 new)

- [2026-03-12 v141](exec-plans/completed/2026/Week-11.md) --
  E2E marker filename constant (`_E2E_MARKER_FILE`), CLI `--pr-number` positive validation, Celery timeout constants (`_KEYCHAIN_TIMEOUT_S`, `_DB_CONNECT_TIMEOUT_S`); 3464 tests (15 new)

- [2026-03-12 v140](exec-plans/completed/2026/Week-11.md) --
  Extract remaining magic numbers (`_APPLY_CHANGES_TRUNCATION_LIMIT`, `_STREAM_READ_BUFFER_SIZE` in cli/base.py, `_DEFAULT_MAX_TOKENS` in anthropic.py), GitHub PR number/limit validation (`get_pr`, `update_pr_body`, `list_prs`), `_truncate_diff` limit safety guard; 3456 tests (20 new)

- [2026-03-12 v139](exec-plans/completed/2026/Week-11.md) --
  Extract hardcoded magic numbers in claude.py (`_TEXT_PREVIEW_MAX_LENGTH`, `_TOOL_RESULT_PREVIEW_MAX_LENGTH`, `_COMMAND_PREVIEW_MAX_LENGTH`), pr_description.py (`_PR_SUMMARY_TRUNCATION_LENGTH`, `_COMMIT_SUMMARY_TRUNCATION_LENGTH`, `_PROMPT_CONTEXT_LENGTH`, `_PR_ERROR_TAIL_LENGTH`, `_COMMIT_ERROR_TAIL_LENGTH`, `_COMMIT_MSG_MAX_LENGTH`), DRY `_FAILURE_OUTPUT_TAIL_LENGTH` across 4 CLI hands, import `_FILE_LIST_PREVIEW_LIMIT` in cli/base.py; 3436 tests (29 new)

- [2026-03-12 v138](exec-plans/completed/2026/Week-11.md) --
  Extract hardcoded magic numbers to module-level constants in Hand base (`_DEFAULT_BASE_BRANCH`, `_DEFAULT_GIT_USER_NAME`, `_DEFAULT_GIT_USER_EMAIL`, `_DEFAULT_CI_WAIT_MINUTES`, `_DEFAULT_CI_MAX_RETRIES`, `_BRANCH_PREFIX`, `_UUID_HEX_LENGTH`, `_MAX_OUTPUT_DISPLAY_LENGTH`, `_FILE_LIST_PREVIEW_LIMIT`, `_LOG_TRUNCATION_LENGTH`), CLI base (`_PROCESS_TERMINATE_TIMEOUT_S`, `_CI_POLL_INTERVAL_S`, `_PR_DESCRIPTION_TIMEOUT_S`), and CLI main (`_DEFAULT_CLONE_DEPTH`, `_TEMP_CLONE_PREFIX`); 3436 tests (31 new)

- [2026-03-12 v137](exec-plans/completed/2026/Week-11.md) --
  Extract health check timeout constants (`_KEYCHAIN_TIMEOUT_S`, `_USAGE_API_TIMEOUT_S`, `_REDIS_HEALTH_TIMEOUT_S`, `_DB_HEALTH_TIMEOUT_S`, `_CELERY_HEALTH_TIMEOUT_S`, `_CELERY_INSPECT_TIMEOUT_S`) in `server/app.py`; DRY Anthropic usage API constants (`_ANTHROPIC_USAGE_URL`, `_ANTHROPIC_BETA_HEADER`, `_USAGE_USER_AGENT`) in both `server/app.py` and `server/celery_app.py`; 3835 tests (17 new)

- [2026-03-12 v136](exec-plans/completed/2026/Week-11.md) --
  Gitignore E2E/Playwright test artifacts (`frontend/test-results/`, `playwright-report/`, `blob-report/`, `coverage.xml`); commit message quality hardening — `_is_trivial_message()` rejects meaningless messages like `feat: -` or `feat: ...` in both `_parse_commit_message` and `_commit_message_from_prompt`; TODO.md items resolved; 3376 tests (27 new)


- [2026-03-11 v135](exec-plans/completed/2026/Week-11.md) --
  Extract hardcoded magic numbers to module-level constants: `_DEFAULT_EXEC_TIMEOUT_S` and `_DEFAULT_BROWSE_MAX_CHARS` in `mcp_server.py`, `_USAGE_LOG_INTERVAL_S` in `celery_app.py`; constant value and function signature default tests (10 tests, 3 skipped without celery)

- [2026-03-11 v134](exec-plans/completed/2026/Week-11.md) --
  _parse_str_list empty/whitespace string rejection (registry.py + iterative.py), _load_env_files tilde expansion test coverage, _collect_celery_current_tasks direct test coverage (7 tests); 3780 passing tests (+ 14 new)

- [2026-03-11 v133](exec-plans/completed/2026/Week-11.md) --
  Warning logging for silent env var fallbacks (_timeout_seconds/_diff_char_limit), git-not-found handling in _get_diff/_get_uncommitted_diff, write_text_file OSError wrapping; 3369 tests (3336 passing, 33 skipped)

- [2026-03-11 v132](exec-plans/completed/2026/Week-11.md) --
  CLI model None guard (_resolve_cli_model treats "None" as default), _resolve_worker_capacity env var test coverage (13 tests), LangGraph run/build_agent/stream test gaps (5 tests); 3361 tests (3328 passing, 33 skipped)
- [2026-03-11 v131](exec-plans/completed/2026/Week-11.md) --
  Network error handling (URLError/HTTPError → RuntimeError) in search_web/browse_url, clone() depth validation, Google provider empty messages guard; 3353 tests (3321 passing, 32 skipped)
- [2026-03-11 v130](exec-plans/completed/2026/Week-11.md) --
  Defensive CI response handling (.get() defaults), frontend form validation (submitRun/saveSchedule emptiness checks), statusBlinkerColor test coverage; 3482 tests (3304+ backend, 178 frontend)
- [2026-03-11 v129](exec-plans/completed/2026/Week-11.md) --
  Exception debug logging in atomic.py/iterative.py, Goose _build_subprocess_env test coverage (10 tests); 3304 passing tests
- [2026-03-11 v128](exec-plans/completed/2026/Week-11.md) --
  Robustness hardening: _load_meta JSON error handling, max_iterations upper bound (1000), _apply_inline_edits OSError safety; 3312 tests
- [2026-03-11 v127](exec-plans/completed/2026/Week-11.md) --
  Input validation hardening for AI providers and server helpers: normalize_messages non-Mapping rejection, AIProvider empty-model guard, _parse_task_kwargs_str max-size guard; 3310 tests
- [2026-03-11 v125-v126](exec-plans/completed/2026/Week-11.md) --
  Type safety, timeout bounds, _is_boilerplate_line tests, input validation hardening (min_length on server requests, bash script mutual exclusivity) and web helper test coverage; 3300 tests
- [2026-03-11 Week 11](exec-plans/completed/2026/Week-11.md) --
  v104-v146: Dead code cleanup, server routing, E2E draft PR, Celery helpers, health checks, ty in CI, Claude CLI emitter hardening, Hand World factory theme, input validation, DRY validators, assert→RuntimeError guards, debug logging, MCP validation, tool summarization expansion, git operation hardening, type safety, timeout bounds, boilerplate line test coverage, robustness hardening, exception debug logging, Goose env test coverage, defensive CI response handling, frontend form validation, network error handling, constant extraction, GitHub PR validation, truncation safety, commit message quality; 3031 -> 3542 passing tests (backend), 153 -> 178 tests (frontend)
- [2026-03-07 Week 10](exec-plans/completed/2026/Week-10.md) --
  v0-v103: Docs infrastructure, 28 design docs, massive validation test suite, provider tests, Config edge cases, Playwright e2e tests, exec-plan workflow; 0 -> 3031 tests
- [2026-03-02 Week 9](exec-plans/completed/2026/Week-9.md) --
  Multi-backend expansion (Goose, Gemini, Ollama), React frontend launch, animated office world view, cron scheduling, usage tracking, skills/tools refactor; 0 tests (pre-test-suite)
- [2026-02-23 Week 8](exec-plans/completed/2026/Week-8.md) --
  Project inception: Hand abstraction, AI providers, Celery, MCP server, GitHub integration, Claude Code CLI, E2E flow; 0 tests (pre-test-suite)

## How plans work

1. Plans are created in `docs/exec-plans/active/` with a descriptive filename
2. Each plan has a status, creation date, tasks, and completion criteria
3. When all tasks are done, the plan moves to `docs/exec-plans/completed/`
4. The tech debt tracker (`docs/exec-plans/tech-debt-tracker.md`) captures
   ongoing technical debt items that don't warrant a full plan
