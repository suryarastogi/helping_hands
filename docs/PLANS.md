# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

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
