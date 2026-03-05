# Quality Score

Metrics and standards for code quality in helping_hands.

## Current quality gates

### CI pipeline (GitHub Actions)

| Check | Tool | Scope | Status |
|---|---|---|---|
| Lint | `ruff check` | All Python | Enforced |
| Format | `ruff format --check` | All Python | Enforced |
| Tests | `pytest -v` | `tests/` | Enforced |
| Coverage | `pytest-cov` + Codecov | Python 3.12 job | Reporting |
| Frontend lint | `eslint` | `frontend/src/` | Enforced |
| Frontend types | `tsc --noEmit` | `frontend/src/` | Enforced |
| Frontend tests | Vitest | `frontend/src/` | Enforced |

### Local quality checks

```bash
uv run ruff check .               # lint
uv run ruff format --check .      # format
uv run pytest -v                  # tests + coverage
uv run pre-commit run --all-files # all hooks
npm --prefix frontend run lint    # frontend lint
npm --prefix frontend run typecheck  # frontend types
npm --prefix frontend run test    # frontend tests
```

## Coverage targets

- **Backend:** Track via Codecov; aim for increasing coverage each PR
- **Frontend:** Track via Codecov (separate flag); aim for component coverage

## Testing conventions

- Tests live in `tests/` (flat structure, `test_*.py` naming)
- Use `pytest` fixtures (`tmp_path`, `monkeypatch`) over manual setup/teardown
- Mock external services (GitHub API, AI providers) in unit tests
- Integration tests are opt-in (`HELPING_HANDS_RUN_E2E_INTEGRATION=1`)

## Ruff configuration

Rules enabled: `E, W, F, I, N, UP, B, SIM, RUF`
Line length: 88
Target Python: 3.12+

## Per-module coverage targets

| Module | Current state | Target | Notes |
|---|---|---|---|
| `lib/config.py` | Good (env loading, overrides, dotenv) | 90%+ | Normalization edge cases added in v5 |
| `lib/repo.py` | Excellent (12 tests, all paths) | Maintained | No gaps identified |
| `lib/meta/tools/filesystem.py` | Excellent (25+ tests, security) | Maintained | Edge cases added in v5 |
| `lib/meta/tools/command.py` | Good (execution paths) | 90%+ | `CommandResult`, `_normalize_args`, `_resolve_cwd` added in v5 |
| `lib/hands/v1/hand/model_provider.py` | Good (resolution) | 90%+ | `_infer_provider_name`, `HandModel` added in v5 |
| `lib/ai_providers/` | Good (init, normalize, complete, _build_inner) | 85%+ | `_build_inner` ImportError + env var paths added in v11 |
| `lib/hands/v1/hand/base.py` | Good (finalization, auth, precommit, PR body) | 85%+ | `_default_base_branch`, `_build_generic_pr_body` added in v8 |
| `lib/hands/v1/hand/cli/` | Good (dedicated test files per backend) | 80%+ | Claude/Codex/Gemini/OpenCode/Goose helpers well-tested; subprocess paths harder |
| `lib/github.py` | Excellent (13 test classes) | Maintained | No gaps identified |
| `server/app.py` | Good (5 test classes) | 85%+ | Additional endpoint edge cases next |
| `lib/hands/v1/hand/iterative.py` | Good (bootstrap, tree, inline edits, parsers) | 80%+ | `_build_tree_snapshot`, `_read_bootstrap_doc`, `_build_bootstrap_context`, `_apply_inline_edits` added in v9 |
| `lib/ai_providers/ollama.py` | Good (env vars, ImportError, kwargs) | 85%+ | `_build_inner`, `_complete_impl` added in v10 |
| `lib/hands/v1/hand/e2e.py` | Good (static methods fully tested) | 80%+ | `_safe_repo_dir`, `_work_base`, `_configured_base_branch`, `_build_e2e_pr_comment`, `_build_e2e_pr_body` added in v10 |
| `server/celery_app.py` | Good (URL helpers, redaction, updates) | 70%+ | `_github_clone_url`, `_redact_sensitive`, `_repo_tmp_dir`, `_trim_updates`, `_append_update`, `_UpdateCollector` added in v10 |
| `server/schedules.py` | Good (ScheduledTask, cron validation, ScheduleManager CRUD) | 80%+ | `_check_redbeat`, `_check_croniter`, ScheduleManager with mocked Redis added in v11 |
| `lib/meta/tools/registry.py` (runners) | Good (runner payload validation + mocked dispatch) | 85%+ | `_run_python_code`, `_run_python_script`, `_run_bash_script`, `_run_web_search`, `_run_web_browse` added in v12 |
| `server/mcp_server.py` | Good (12 test classes) | 85%+ | `_repo_root`, `_command_result_to_dict`, error paths (IsADirectory, Unicode, path traversal) added in v12; fixed UnicodeError handler ordering |
| `server/app.py` (helpers) | Good (12 test classes) | 85%+ | `_parse_backend`, `_task_state_priority`, `_normalize_task_status`, `_extract_task_id/name/kwargs`, `_coerce_optional_str`, `_parse_task_kwargs_str`, `_is_helping_hands_task`, `_upsert_current_task`, `_flower_timeout_seconds`, `_flower_api_base_url` added in v13 |
| `lib/hands/v1/hand/cli/base.py` (CI/PR) | Good (6 test classes) | 80%+ | `_build_ci_fix_prompt`, `_format_ci_fix_message`, `_format_pr_status_message`, `_looks_like_edit_request` added in v13 |
| `cli/main.py` (helpers) | Good (6 test classes) | 93%+ | `_github_clone_url`, `_git_noninteractive_env`, `_redact_sensitive`, `_repo_tmp_dir`, `opencodecli` backend, `model_not_found` error, invalid `--tools` added in v14 |
| `lib/hands/v1/hand/model_provider.py` (builders) | Excellent (99% coverage) | Maintained | `build_langchain_chat_model` (all 5 providers + ImportError paths + env vars), `build_atomic_client` (OpenAI, LiteLLM + missing attr, unsupported) added in v15 |
| `lib/ai_providers/openai.py` | Good (dedicated tests) | 85%+ | `_build_inner` (ImportError, with/without API key), `_complete_impl` (delegation, kwargs) added in v16 |
| `lib/ai_providers/google.py` | Good (build_inner + complete_impl) | 85%+ | `_complete_impl` (delegation, empty content filtering, kwargs) added in v16; `_build_inner` covered in v11 |
| `lib/hands/v1/hand/cli/claude.py` | Excellent (92% coverage) | Maintained | `_command_not_found_message`, `_native_cli_auth_env_names`, `_pr_description_cmd` added in v16 |
| `lib/hands/v1/hand/cli/base.py` (helpers) | Good (74% coverage) | 80%+ | `_resolve_cli_model`, `_inject_prompt_argument`, `_normalize_base_command`, `_build_failure_message`, `_describe_auth`, `_effective_container_env_names`, `_build_subprocess_env`, `_interrupted_pr_metadata` added in v17 |
| `lib/ai_providers/anthropic.py` | Good (complete_impl kwargs) | 85%+ | Extra kwargs forwarding test added in v17 |
| `lib/ai_providers/litellm.py` | Good (complete_impl kwargs) | 85%+ | Extra kwargs forwarding test added in v17 |
| `lib/hands/v1/hand/base.py` (statics) | Good (66% -> 70%+) | 75%+ | `_github_repo_from_origin` edge cases (empty/non-GitHub/SSH/single-segment), `_run_precommit_checks_and_fixes` (FileNotFoundError, output truncation, first-pass success), `_push_noninteractive` (env save/restore, failure recovery), `_push_to_existing_pr` (success/diverged/different-user), `_should_run_precommit_before_pr`, `_finalize_repo_pr` error paths (missing_token, git_error, generic) added in v18 |
| `lib/meta/tools/command.py` | Good (73% -> 85%+) | 85%+ | `_resolve_python_command` (uv/direct/neither/empty), `_run_command` timeout (with/without output, zero/negative), `run_python_code` empty validation, `run_python_script` (missing/directory), `run_bash_script` (missing/directory/empty-both/inline-args) added in v18 |
| `lib/hands/v1/hand/cli/base.py` (prompts/container) | Good (74% -> 78%+) | 80%+ | `_execution_mode`, `_container_enabled` (env var truthy/falsy/missing/empty/no-config), `_container_image` (set/missing/empty/no-config/whitespace), `_apply_verbose_flags` (on/off/duplicates/no-flags), `_build_init_prompt` (repo root, file list, cap at 200, empty list), `_build_task_prompt` (prompt, summary, truncation, placeholder), `_build_apply_changes_prompt` (prompt, output, truncation, placeholder) added in v19 |
| `lib/hands/v1/hand/cli/base.py` (command/timing) | Good (75% -> 76%+) | 80%+ | `_base_command` (default/env override/empty raises), `_io_poll_seconds`/`_heartbeat_seconds`/`_idle_timeout_seconds` (defaults/env overrides/verbose heartbeat), `_repo_has_changes` (with changes/clean/non-git) added in v20 |
| `lib/hands/v1/hand/cli/base.py` (retry/interrupt) | Good (76% -> 77%+) | 80%+ | `_should_retry_without_changes` (all 4 branches: feature off, interrupted, not edit, has changes), `_no_change_error_after_retries` (base returns None), `_build_apply_changes_prompt` (prompt+output, empty output, truncation), `_terminate_active_process` (None/exited/terminate/kill-on-timeout), `interrupt()` (active/None/exited) added in v22 |
| `lib/hands/v1/hand/iterative.py` (iteration helpers) | Good (76% -> 78%+) | 80%+ | `_build_iteration_prompt`, `_execution_tools_enabled`/`_web_tools_enabled`, `_tool_instructions`, `BasicLangGraphHand._result_content`, `BasicAtomicHand._extract_message` added in v20; `_execute_read_requests` error paths (ValueError/FileNotFoundError/IsADirectoryError/UnicodeError), `_run_tool_request` dispatch (WebSearchResult/WebBrowseResult/unsupported/disabled), `_execute_tool_requests` error pass-through added in v21; fixed UnicodeError handler ordering bug (same as mcp_server.py v12) |

## Areas for improvement

- [ ] Add type checking to CI (ty, when stable for CI runners)
- [ ] Add mutation testing for critical path safety (filesystem tools)
- [ ] Increase coverage for CLI hand subprocess wrappers
- [ ] Add load testing for app mode concurrent task handling
- [x] Add tests for `_build_tree_snapshot` / `_build_bootstrap_context` (iterative.py) — added in v9
- [x] Add tests for `_read_bootstrap_doc` / `_apply_inline_edits` (iterative.py, needs tmp_path) — added in v9
