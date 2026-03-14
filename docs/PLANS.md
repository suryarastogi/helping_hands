# Plans

Index of execution plans for helping_hands development.

## Active plans

(none)

## Completed plans

- [2026-03-14 v166](exec-plans/completed/2026-03-14.md) --
  Consolidate `_FAILURE_OUTPUT_TAIL_LENGTH` to cli/base.py (DRY 4 copies), harmonize `_is_truthy` with config `_TRUTHY_VALUES` via `_CLI_TRUTHY_VALUES`, add Google-style docstrings to codex.py (12) and gemini.py (14); 3986 tests (42 new)

- [2026-03-14 v165](exec-plans/completed/2026-03-14.md) --
  Extract command exit code constants (124/127/126), DRY boolean env parsing (`_TRUTHY_VALUES`/`_is_truthy_env`), add Google-style docstrings to 7 CLI hand methods; 3944 tests (34 new)


- [2026-03-14 v164](exec-plans/completed/2026-03-14.md) --
  Close 10 uncovered lines: Hand base.py pr_number None guards (3 tests), pr_description.py multi-word keywords + second FileNotFoundError + empty-line skip (4 tests), claude.py empty model guard (1 test); 3910 tests (8 new)

- [2026-03-14 v163](exec-plans/completed/2026-03-14.md) --
  Add Google-style docstrings to 9 Hand base.py methods, extract 6 Claude CLI stream-json event type constants; 3902 tests (22 new)


- [2026-03-14 v162](exec-plans/completed/2026-03-14.md) --
  Extract bootstrap doc constants (`_README_CANDIDATES`, `_AGENT_DOC_CANDIDATES`), DRY backend name class constants (`_BACKEND_NAME`), add Google-style docstrings to 8 key methods in iterative.py; 3880 tests (22 new)

- [2026-03-14 v161](exec-plans/completed/2026-03-14.md) --
  Add `__all__` exports to 13 remaining modules: hand base/e2e/iterative, 6 CLI hands (claude/codex/gemini/goose/opencode/docker_sandbox_claude), server app/celery/mcp, CLI main; 3858 tests (48 new: 35 passed, 13 skipped without server extras)

- [2026-03-13 v160](exec-plans/completed/2026-03-13.md) --
  Task cancellation (kill signal from UI): `POST /tasks/{task_id}/cancel` endpoint, cancel button in inline HTML + React frontend, Celery `revoke(terminate=True)`; 4367 tests (15 new)

- [2026-03-13 v159](exec-plans/completed/2026-03-13.md) --
  Add `__all__` to 8 modules: 5 AI providers (openai, anthropic, google, litellm, ollama), pr_description, model_provider, schedules; 3809 tests (48 new: 38 passed, 10 skipped)

- [2026-03-13 v158](exec-plans/completed/2026-03-13.md) --
  Add `__all__` to web.py/repo.py/default_prompts.py/task_result.py, extract `_DUCKDUCKGO_API_URL` in web.py, `normalize_relative_path` empty-string validation; 3772 tests (29 new)

- [2026-03-13 v157](exec-plans/completed/2026-03-13.md) --
  Add `__all__` exports to types.py, github.py, filesystem.py, command.py; enhance `normalize_messages()` docstring to Google-style with Args/Returns/Raises; 3743 tests (27 new)


- [2026-03-13 v156](exec-plans/completed/2026-03-13.md) --
  Config.from_env() whitespace stripping (`repo`/`model`/`github_token`), `__all__` export in config.py, `_build_generic_pr_body` input validation, `_is_git_hook_failure` edge case tests; 3716 tests (16 new)

- [2026-03-13 v155](exec-plans/completed/2026-03-13.md) --
  Input validation and defensive coding: `read_text_file()` `max_file_size` positive validation, Google provider `_complete_impl()` KeyError defense, `_get_diff()` fallback test coverage; 3700 tests (14 new)

- [2026-03-13 v154](exec-plans/completed/2026-03-13.md) --
  Git subprocess timeouts for `pr_description.py` diff/add calls, `cli/main.py` and `celery_app.py` clone calls, `read_text_file()` `max_chars` positive validation; 3687 tests (21 new)

- [2026-03-13 v153](exec-plans/completed/2026-03-13.md) --
  Subprocess timeouts for `_configure_authenticated_push_remote()` and `_run_precommit_checks_and_fixes()`, input validation for `_configure_authenticated_push_remote()` repo/token params and `GitHubClient.clone()` full_name; 3666 tests (16 new)


- [2026-03-13 v152](exec-plans/completed/2026-03-13.md) --
  Remove 7 stale `ty: ignore` comments causing CI `unused-ignore-comment` warnings (model_provider.py, celery_app.py, schedules.py); 3649 tests (5 new regression guards)

- [2026-03-13 v151](exec-plans/completed/2026-03-13.md) --
  Input type validation: `normalize_relative_path` non-string TypeError, `normalize_tool_selection`/`normalize_skill_selection` dict/set/int rejection, `_truncate_summary` positive limit guard; 3644 tests (28 new)

- [2026-03-13 v150](exec-plans/completed/2026-03-13.md) --
  GitHubClient method input validation hardening: `create_pr()` title/head/base, `list_prs()` `_VALID_PR_STATES` enum, `get_check_runs()` ref, `upsert_pr_comment()` number/body; 3619 tests (20 new)

- [2026-03-13 v149](exec-plans/completed/2026-03-13.md) --
  Git subprocess timeouts (`_run_git_read`, `_repo_has_changes`), clone URL `_validate_repo_spec()`, error message redaction; 3599 tests (17 new)

- [2026-03-13 v148](exec-plans/completed/2026-03-13.md) --
  Remove hardcoded DB credentials in `_get_db_url_writer()` (security fix), GitHubClient branch/commit input validation (`_validate_branch_name`, empty message/name/email guards); 3582 tests (19 new)

- [2026-03-13 v147](exec-plans/completed/2026-03-13.md) --
  Per-task GitHub token override (Config → CLI → server → Celery → GitHubClient), dead code removal, constant docstrings; 3563 tests (21 new)

- [2026-03-12 v146](exec-plans/completed/2026-03-12.md) --
  Commit message quality: `_truncate_text()` truncation indicators for prompt/summary context, `_infer_commit_type()` smart type inference replacing hardcoded `"feat:"` prefix; 3542 tests (48 new)

- [2026-03-12 v145](exec-plans/completed/2026-03-12.md) --
  Extract keychain constants (`_KEYCHAIN_SERVICE_NAME`, `_KEYCHAIN_OAUTH_KEY`, `_KEYCHAIN_ACCESS_TOKEN_KEY`) in app.py and celery_app.py, utilization numeric type guard, decode safety with `errors="replace"`; 3494 tests (20 new)

- [2026-03-12 v144](exec-plans/completed/2026-03-12.md) --
  MCP index file limit constant (`_INDEX_FILES_LIMIT`), JWT token prefix constant (`_JWT_TOKEN_PREFIX`) in app.py and celery_app.py, E2E UUID hex length reuse from base.py; 3494 tests (15 new)

- [2026-03-12 v143](exec-plans/completed/2026-03-12.md) --
  Redis write/delete/list error handling in schedules.py (`_save_meta`, `_delete_meta`, `_list_meta_keys`), extract `_SCHEDULE_ID_HEX_LENGTH` in schedules.py, extract `_OLLAMA_DEFAULT_HOST` in goose.py; 3487 tests (7 new)

- [2026-03-12 v142](exec-plans/completed/2026-03-12.md) --
  Extract remaining magic numbers (`_HTTP_ERROR_BODY_PREVIEW_LENGTH`, `_USAGE_DATA_PREVIEW_LENGTH` in server/app.py, `_HOOK_ERROR_TRUNCATION_LIMIT`, `_GIT_REF_DISPLAY_LENGTH` in cli/base.py, `_SANDBOX_NAME_MAX_LENGTH`, `_SANDBOX_UUID_HEX_LENGTH` in docker_sandbox_claude.py), RepoIndex PermissionError handling in repo.py; 3480 tests (26 new)

- [2026-03-12 v141](exec-plans/completed/2026-03-12.md) --
  E2E marker filename constant (`_E2E_MARKER_FILE`), CLI `--pr-number` positive validation, Celery timeout constants (`_KEYCHAIN_TIMEOUT_S`, `_DB_CONNECT_TIMEOUT_S`); 3464 tests (15 new)

- [2026-03-12 v140](exec-plans/completed/2026-03-12.md) --
  Extract remaining magic numbers (`_APPLY_CHANGES_TRUNCATION_LIMIT`, `_STREAM_READ_BUFFER_SIZE` in cli/base.py, `_DEFAULT_MAX_TOKENS` in anthropic.py), GitHub PR number/limit validation (`get_pr`, `update_pr_body`, `list_prs`), `_truncate_diff` limit safety guard; 3456 tests (20 new)

- [2026-03-12 v139](exec-plans/completed/2026-03-12.md) --
  Extract hardcoded magic numbers in claude.py (`_TEXT_PREVIEW_MAX_LENGTH`, `_TOOL_RESULT_PREVIEW_MAX_LENGTH`, `_COMMAND_PREVIEW_MAX_LENGTH`), pr_description.py (`_PR_SUMMARY_TRUNCATION_LENGTH`, `_COMMIT_SUMMARY_TRUNCATION_LENGTH`, `_PROMPT_CONTEXT_LENGTH`, `_PR_ERROR_TAIL_LENGTH`, `_COMMIT_ERROR_TAIL_LENGTH`, `_COMMIT_MSG_MAX_LENGTH`), DRY `_FAILURE_OUTPUT_TAIL_LENGTH` across 4 CLI hands, import `_FILE_LIST_PREVIEW_LIMIT` in cli/base.py; 3436 tests (29 new)

- [2026-03-12 v138](exec-plans/completed/2026-03-12.md) --
  Extract hardcoded magic numbers to module-level constants in Hand base (`_DEFAULT_BASE_BRANCH`, `_DEFAULT_GIT_USER_NAME`, `_DEFAULT_GIT_USER_EMAIL`, `_DEFAULT_CI_WAIT_MINUTES`, `_DEFAULT_CI_MAX_RETRIES`, `_BRANCH_PREFIX`, `_UUID_HEX_LENGTH`, `_MAX_OUTPUT_DISPLAY_LENGTH`, `_FILE_LIST_PREVIEW_LIMIT`, `_LOG_TRUNCATION_LENGTH`), CLI base (`_PROCESS_TERMINATE_TIMEOUT_S`, `_CI_POLL_INTERVAL_S`, `_PR_DESCRIPTION_TIMEOUT_S`), and CLI main (`_DEFAULT_CLONE_DEPTH`, `_TEMP_CLONE_PREFIX`); 3436 tests (31 new)

- [2026-03-12 v137](exec-plans/completed/2026-03-12.md) --
  Extract health check timeout constants (`_KEYCHAIN_TIMEOUT_S`, `_USAGE_API_TIMEOUT_S`, `_REDIS_HEALTH_TIMEOUT_S`, `_DB_HEALTH_TIMEOUT_S`, `_CELERY_HEALTH_TIMEOUT_S`, `_CELERY_INSPECT_TIMEOUT_S`) in `server/app.py`; DRY Anthropic usage API constants (`_ANTHROPIC_USAGE_URL`, `_ANTHROPIC_BETA_HEADER`, `_USAGE_USER_AGENT`) in both `server/app.py` and `server/celery_app.py`; 3835 tests (17 new)

- [2026-03-12 v136](exec-plans/completed/2026-03-12.md) --
  Gitignore E2E/Playwright test artifacts (`frontend/test-results/`, `playwright-report/`, `blob-report/`, `coverage.xml`); commit message quality hardening — `_is_trivial_message()` rejects meaningless messages like `feat: -` or `feat: ...` in both `_parse_commit_message` and `_commit_message_from_prompt`; TODO.md items resolved; 3376 tests (27 new)


- [2026-03-11 v135](exec-plans/completed/2026-03-11.md) --
  Extract hardcoded magic numbers to module-level constants: `_DEFAULT_EXEC_TIMEOUT_S` and `_DEFAULT_BROWSE_MAX_CHARS` in `mcp_server.py`, `_USAGE_LOG_INTERVAL_S` in `celery_app.py`; constant value and function signature default tests (10 tests, 3 skipped without celery)

- [2026-03-11 v134](exec-plans/completed/2026-03-11.md) --
  _parse_str_list empty/whitespace string rejection (registry.py + iterative.py), _load_env_files tilde expansion test coverage, _collect_celery_current_tasks direct test coverage (7 tests); 3780 passing tests (+ 14 new)

- [2026-03-11 v133](exec-plans/completed/2026-03-11.md) --
  Warning logging for silent env var fallbacks (_timeout_seconds/_diff_char_limit), git-not-found handling in _get_diff/_get_uncommitted_diff, write_text_file OSError wrapping; 3369 tests (3336 passing, 33 skipped)

- [2026-03-11 v132](exec-plans/completed/2026-03-11.md) --
  CLI model None guard (_resolve_cli_model treats "None" as default), _resolve_worker_capacity env var test coverage (13 tests), LangGraph run/build_agent/stream test gaps (5 tests); 3361 tests (3328 passing, 33 skipped)
- [2026-03-11 v131](exec-plans/completed/2026-03-11.md) --
  Network error handling (URLError/HTTPError → RuntimeError) in search_web/browse_url, clone() depth validation, Google provider empty messages guard; 3353 tests (3321 passing, 32 skipped)
- [2026-03-11 v130](exec-plans/completed/2026-03-11.md) --
  Defensive CI response handling (.get() defaults), frontend form validation (submitRun/saveSchedule emptiness checks), statusBlinkerColor test coverage; 3482 tests (3304+ backend, 178 frontend)
- [2026-03-11 v129](exec-plans/completed/2026-03-11.md) --
  Exception debug logging in atomic.py/iterative.py, Goose _build_subprocess_env test coverage (10 tests); 3304 passing tests
- [2026-03-11 v128](exec-plans/completed/2026-03-11.md) --
  Robustness hardening: _load_meta JSON error handling, max_iterations upper bound (1000), _apply_inline_edits OSError safety; 3312 tests
- [2026-03-11 v127](exec-plans/completed/2026-03-11.md) --
  Input validation hardening for AI providers and server helpers: normalize_messages non-Mapping rejection, AIProvider empty-model guard, _parse_task_kwargs_str max-size guard; 3310 tests
- [2026-03-11 v125-v126](exec-plans/completed/2026-03-11.md) --
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
