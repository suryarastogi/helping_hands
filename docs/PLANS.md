# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [Docs and Testing v36](exec-plans/completed/docs-and-testing-v36.md) --
  GitHub client edge case tests (`fetch_branch` default/custom remote, `pull` with branch, `set_local_identity`, `get_check_runs` mixed conclusion, `upsert_pr_comment` body-already-has-marker/None-body); Hand base.py edge case tests (`_push_to_existing_pr` whoami exception, `_finalize_repo_pr` precommit-no-changes-after-fix, `_finalize_repo_pr` get_repo default_branch exception fallback); DESIGN.md updated with GitHub client patterns and finalization resilience; 1290 tests pass (completed 2026-03-06)

- [Docs and Testing v35](exec-plans/completed/docs-and-testing-v35.md) --
  Server health check and config helper tests (`_check_redis_health` ok/error, `_check_db_health` na/ok/error, `_check_workers_health` ok/none/empty/exception, `_is_running_in_docker` dockerenv/env var/neither, `_iter_worker_task_entries` valid/non-dict/non-list/non-dict entries, `_safe_inspect_call` success/missing/exception); celery_app `_has_codex_auth` tests (env var/auth file/neither/empty); DESIGN.md updated with health check and server config patterns; 1514 tests pass (completed 2026-03-06)

- [Docs and Testing v34](exec-plans/completed/docs-and-testing-v34.md) --
  E2EHand.run() unit tests with mocked GitHubClient (dry-run/fresh-PR/resumed-PR/empty-repo/configured-base-branch/default-branch-fallback/auto-uuid), E2EHand.stream() yield test, placeholders.py backward-compat shim tests (re-exports, module aliases, identity checks); e2e.py coverage 25% -> 98%; 1278 tests pass (completed 2026-03-06)

- [Docs and Testing v33](exec-plans/completed/docs-and-testing-v33.md) --
  Schedule module edge case tests (`trigger_now` happy path/missing/param forwarding, `get_schedule_manager`, `create_schedule` enabled/disabled branches, `update_schedule` enabled/disabled branches, `_create_redbeat_entry` invalid cron validation, `_delete_redbeat_entry` KeyError handling, `list_schedules` None filtering, `ScheduledTask` fix_ci/ci_check_wait_minutes roundtrip); DESIGN.md updated with scheduling pattern; schedules.py 80% -> 93%; 1473 tests pass (completed 2026-03-06)

- [Docs and Testing v32](exec-plans/completed/docs-and-testing-v32.md) —
  pr_description.py edge case tests (`_diff_char_limit` negative, `_get_diff` empty stdout on success, `_build_prompt`/`_build_commit_message_prompt` summary truncation, `_parse_output` whitespace-only body, `_commit_message_from_prompt` whitespace edge cases); DESIGN.md updated with PR description generation pattern; 1263 tests pass (completed 2026-03-06)

- [Docs and Testing v31](exec-plans/completed/docs-and-testing-v31.md) —
  Fixed ARCHITECTURE.md key file paths table formatting (merged dangling Docker sandbox entry); _StreamJsonEmitter edge case tests (empty text block, result without cost/duration, partial api summary, empty/whitespace tool_result content, non-tool_result blocks, non-dict list items, empty flush, multiple newlines, unknown event type); _invoke_claude/_invoke_backend async tests (emitter wiring, raw fallback, delegation); claude.py coverage maintained at 97%; 1256 tests pass (completed 2026-03-05)

- [Docs and Testing v30](exec-plans/completed/docs-and-testing-v30.md) —
  Config edge case tests (`_load_env_files` no-dotenv early return, bool tool/skill override normalization to empty tuple); skills edge case tests (`normalize_skill_selection` non-string ValueError, `stage_skill_catalog` missing .md skip); ARCHITECTURE.md + DESIGN.md updated with DockerSandboxClaudeCodeHand; config.py 89%+, skills 94% -> 96%; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v29](exec-plans/completed/docs-and-testing-v29.md) —
  CLI base.py skill catalog + container + task prompt branch tests (19 tests: `_stage_skill_catalog` staging/no-op, `_cleanup_skill_catalog` remove/no-op, `_wrap_container_if_enabled` disabled/docker-not-found/env-forwarding/mount, `_build_task_prompt` tool/skill sections include/omit); Hand base.py early return tests (`_run_git_read` success/failure, `_finalize_repo_pr` no_repo/not_git_repo/no_changes/disabled/no_github_origin); cli/base.py 91% -> 92%, base.py 92% -> 95%; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v28](exec-plans/completed/docs-and-testing-v28.md) —
  celery_app.py helper tests (14 tests: `_resolve_celery_urls` all-defaults, `_resolve_repo_path` local dir/invalid format/clone failure/PR number, `_normalize_backend` whitespace+case/opencodecli/e2e, `_has_gemini_auth` empty/whitespace, `_update_progress` callable/non-callable/workspace, `_collect_stream` chunks+progress); celery_app.py coverage 70% -> 73%; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v27](exec-plans/completed/docs-and-testing-v27.md) —
  DockerSandboxClaudeCodeHand unit tests (36 tests: class attrs, `_resolve_sandbox_name` env/auto/cache/sanitize, `_should_cleanup` truthy/falsy, `_wrap_sandbox_exec` wrapping/env forwarding, `_execution_mode`, `_build_failure_message` auth/generic/sandbox note, `_command_not_found_message`, `_fallback_command_when_not_found`, `_docker_sandbox_available` success/fail/FileNotFoundError, `_ensure_sandbox` skip/docker-not-found/plugin-unavailable/success/failure/template, `_remove_sandbox` skip/stop+rm); docker_sandbox_claude.py coverage 19% -> 91%; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v26](exec-plans/completed/docs-and-testing-v26.md) —
  BasicLangGraphHand.stream() tests (8 tests: satisfied/max-iter/interrupt/file-changes/PR metadata/auth header); BasicAtomicHand.stream() tests (8 tests: satisfied/max-iter/interrupt/assertion-fallback/awaitable/PR status/auth header); OpenCodeCLIHand edge cases (`_build_failure_message` delegation, auth token variations, exit code); base.py PR helpers (`_update_pr_description` rich/fallback/exception-suppressed, `_create_pr_for_diverged_branch` rich/fallback); iterative.py coverage 79% -> 92%; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v25](exec-plans/completed/docs-and-testing-v25.md) —
  Gemini CLI hand helper tests (`_describe_auth` key set/not set/empty, `_pr_description_cmd` found/not found, `_command_not_found_message`); Codex CLI hand helper tests (`_command_not_found_message`, `_native_cli_auth_env_names`, `_apply_codex_exec_sandbox_defaults` empty/whitespace env override fallback); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v24](exec-plans/completed/docs-and-testing-v24.md) —
  CLI base.py CI fix loop tests (`_ci_fix_loop` all early-return paths, success/no_checks/pending/failure conclusions, fix-with-changes, exhausted retries, interrupt, exception error status; `_poll_ci_checks` immediate/deadline paths; `run()` collect+finalize with/without CI fix; `stream()` chunk yielding and PR status); web.py helper edge case tests (`_extract_related_topics` recursive/skip paths, `_require_http_url` extra validation, `_strip_html` noscript/blank-lines, `search_web` dedup/validation/format, `browse_url` non-HTML/validation); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v23](exec-plans/completed/docs-and-testing-v23.md) —
  Fix schedule test collection errors (importorskip guards); AtomicHand unit tests (_build_agent, run(), stream() with 5 async paths); LangGraphHand unit tests (_build_agent, run(), stream() with event filtering); GooseCLIHand helper tests (_describe_auth, _normalize_base_command, _pr_description_cmd, _has_goose_builtin_flag, _apply_backend_defaults, _resolve_ollama_host); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v22](exec-plans/completed/docs-and-testing-v22.md) —
  CLI hand retry/interrupt tests: `_should_retry_without_changes` (all 4 branches), `_no_change_error_after_retries` (base returns None), `_build_apply_changes_prompt` (formatting, empty output, truncation), `_terminate_active_process` (None/exited/terminate/kill-on-timeout), `interrupt()` (active/None/exited); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v21](exec-plans/completed/docs-and-testing-v21.md) —
  Iterative hand `_execute_read_requests` error path tests (ValueError, FileNotFoundError, IsADirectoryError, UnicodeError); `_run_tool_request` dispatch tests (WebSearchResult, WebBrowseResult, unsupported type, disabled tool); `_execute_tool_requests` error handling tests; fixed UnicodeError handler ordering bug in iterative.py; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v20](exec-plans/completed/docs-and-testing-v20.md) —
  Iterative hand helper tests (`_build_iteration_prompt`, `_execution_tools_enabled`/`_web_tools_enabled`, `_tool_instructions`, `BasicLangGraphHand._result_content`, `BasicAtomicHand._extract_message`); CLI base.py tests (`_base_command`, `_io_poll_seconds`/`_heartbeat_seconds`/`_idle_timeout_seconds`, `_repo_has_changes`); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v19](exec-plans/completed/docs-and-testing-v19.md) —
  CLI base.py prompt builder and container/verbose helper tests (`_execution_mode`, `_container_enabled`, `_container_image`, `_apply_verbose_flags`, `_build_init_prompt`, `_build_task_prompt`, `_build_apply_changes_prompt`); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v18](exec-plans/completed/docs-and-testing-v18.md) —
  Hand base.py static/classmethod tests (`_github_repo_from_origin` edge cases, `_run_precommit_checks_and_fixes` FileNotFoundError/truncation, `_push_noninteractive`, `_push_to_existing_pr`, `_should_run_precommit_before_pr`, `_finalize_repo_pr` error paths); command.py gap tests (`_resolve_python_command`, `_run_command` timeout, `run_python_code`/`run_python_script`/`run_bash_script` validation); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v17](exec-plans/completed/docs-and-testing-v17.md) —
  CLI base.py helper tests (`_resolve_cli_model`, `_inject_prompt_argument`, `_normalize_base_command`, `_build_failure_message`, `_describe_auth`, `_effective_container_env_names`, `_build_subprocess_env`, `_interrupted_pr_metadata`); Anthropic and LiteLLM `_complete_impl` extra kwargs tests; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v16](exec-plans/completed/docs-and-testing-v16.md) —
  OpenAI provider `_build_inner()`/`_complete_impl()` tests; Google provider `_complete_impl()` tests; ClaudeCodeHand additional helper tests (`_command_not_found_message`, `_native_cli_auth_env_names`, `_pr_description_cmd`); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v15](exec-plans/completed/docs-and-testing-v15.md) —
  `build_langchain_chat_model()` tests (all 5 providers, ImportError paths, Ollama env vars); `build_atomic_client()` tests (OpenAI, LiteLLM, missing attr, unsupported); provider abstraction design doc; QUALITY_SCORE.md updates (completed 2026-03-05)


- [Docs and Testing v14](exec-plans/completed/docs-and-testing-v14.md) —
  CLI main.py static helper tests (_github_clone_url, _git_noninteractive_env, _redact_sensitive, _repo_tmp_dir); additional backend path tests (opencodecli, model_not_found, invalid tools); ARCHITECTURE.md key file paths refresh; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v13](exec-plans/completed/docs-and-testing-v13.md) —
  App.py pure helper tests (_parse_backend, _task_state_priority, _normalize_task_status, _extract_task_id/name/kwargs, _coerce_optional_str, _parse_task_kwargs_str, _is_helping_hands_task, _upsert_current_task, _flower_timeout_seconds, _flower_api_base_url); CLI base.py CI/PR helper tests (_build_ci_fix_prompt, _format_ci_fix_message, _format_pr_status_message, _looks_like_edit_request); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v12](exec-plans/completed/docs-and-testing-v12.md) —
  Registry runner wrapper tests (payload validation + mocked dispatch for all 5 runners), MCP server error path tests (_repo_root, _command_result_to_dict, read_file IsADirectory/Unicode/path-traversal, write_file path-traversal); fixed UnicodeError handler ordering bug in mcp_server.py; QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v11](exec-plans/completed/docs-and-testing-v11.md) —
  Provider `_build_inner()` tests (LiteLLM, Google, Anthropic — ImportError + env var paths), `_check_redbeat`/`_check_croniter` tests, ScheduleManager unit tests with mocked Redis (CRUD, enable/disable, record_run); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v10](exec-plans/completed/docs-and-testing-v10.md) —
  Ollama provider tests, E2E hand static method tests, celery_app helper tests (_github_clone_url, _redact_sensitive, _repo_tmp_dir, _trim_updates, _append_update, _UpdateCollector); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v9](exec-plans/completed/docs-and-testing-v9.md) —
  Bootstrap and inline edit tests (_build_tree_snapshot, _read_bootstrap_doc, _build_bootstrap_context, _apply_inline_edits); QUALITY_SCORE.md updates (completed 2026-03-05)


- [Docs and Testing v8](exec-plans/completed/docs-and-testing-v8.md) —
  Format helper tests (CommandResult, WebSearchResult, WebBrowseResult), tool config helpers, base.py static helpers (_default_base_branch, _build_generic_pr_body); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v7](exec-plans/completed/docs-and-testing-v7.md) —
  Dedicated test suites for Claude, Codex, Gemini, OpenCode CLI hands (106 tests); DESIGN.md CLI backend patterns (completed 2026-03-05)
- [Docs and Testing v6](exec-plans/completed/docs-and-testing-v6.md) —
  CLI hand helpers, web tool internals, registry validators test coverage; SECURITY.md & RELIABILITY.md iterative hand docs (completed 2026-03-05)
- [Docs and Testing v5](exec-plans/completed/docs-and-testing-v5.md) —
  Pure helper test coverage (model_provider, command, config, filesystem), QUALITY_SCORE.md & RELIABILITY.md enhancements (completed 2026-03-05)
- [Docs and Testing v4](exec-plans/completed/docs-and-testing-v4.md) —
  AI provider & CLI hand test expansion, two-phase CLI hands design doc, SECURITY.md sandboxing (completed 2026-03-04)
- [Docs and Testing v3](exec-plans/completed/docs-and-testing-v3.md) —
  Iterative hand tests, ARCHITECTURE.md data flows, FRONTEND.md expansion (completed 2026-03-04)
- [Docs and Testing v2](exec-plans/completed/docs-and-testing-v2.md) —
  Fill documentation gaps and add targeted tests for untested modules (completed 2026-03-04)
- [Improve Docs and Testing](exec-plans/completed/improve-docs-and-testing.md) —
  Established docs structure, filled initial testing gaps (completed 2026-03-04)

## How plans work

1. Plans are created in `docs/exec-plans/active/` with a descriptive filename
2. Each plan has a status, creation date, tasks, and completion criteria
3. When all tasks are done, the plan moves to `docs/exec-plans/completed/`
4. The tech debt tracker (`docs/exec-plans/tech-debt-tracker.md`) captures
   ongoing technical debt items that don't warrant a full plan
