# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [Docs and Testing v62](exec-plans/completed/docs-and-testing-v62.md) --
  Consolidate 2026-03-04 (v1-v4) and 2026-03-05 (v5-v31) plans into date-based files; add tests/conftest.py with shared `repo_index` and `fake_config` fixtures; refactor test_hand.py, test_hand_base_statics.py to use shared fixtures; 1485 tests pass (completed 2026-03-06)

- [Docs and Testing v61](exec-plans/completed/docs-and-testing-v61.md) --
  Document remaining dead code gaps (web.py latin-1 fallback, mcp_server.py entry guard) in tech-debt-tracker; add testing methodology design doc; add remaining coverage gaps table to QUALITY_SCORE.md; 1485 tests pass (completed 2026-03-06)

- [Docs and Testing v60](exec-plans/completed/docs-and-testing-v60.md) --
  Close remaining branch gaps: model_provider.py unrecognized provider/model slash fallthrough (100%); docker_sandbox_claude.py verbose=False and sandbox-in-base branches (100%); skills/__init__.py no-heading catalog discovery (100%); registry.py empty inner token skip (100%); document cli/main.py and cli/base.py untestable gaps in tech-debt-tracker; 1485 tests pass (completed 2026-03-06)

- [Docs and Testing v59](exec-plans/completed/docs-and-testing-v59.md) --
  Close e2e.py `current_branch` detection branch gap (falsy detected path); document e2e.py `final_pr_number is None` dead code in tech-debt-tracker; add testing patterns section to DESIGN.md; 1478 tests pass (completed 2026-03-06)

- [Docs and Testing v58](exec-plans/completed/docs-and-testing-v58.md) --
  Close claude.py `_StreamJsonEmitter` branch gaps (unknown content block type, whitespace-only text preview) and `_skip_permissions_enabled` geteuid-not-callable path; add skills `normalize_skill_selection` whitespace-only token test; fix stale `server/__init__.py` docstring; add error recovery patterns to DESIGN.md; claude.py 99%+; all tests pass (completed 2026-03-06)

- [Docs and Testing v57](exec-plans/completed/docs-and-testing-v57.md) --
  Close atomic.py `stream()` non-AssertionError exception propagation gap (lines 91-92); add skill catalog pattern to DESIGN.md; add Docker sandbox reliability and async compatibility fallback patterns to RELIABILITY.md; atomic.py 97% -> 98%+; 1473 backend tests pass (completed 2026-03-06)

- [Docs and Testing v56](exec-plans/completed/docs-and-testing-v56.md) --
  Close iterative.py `_build_agent` coverage gaps for BasicLangGraphHand (lines 507-518) and BasicAtomicHand (lines 696-713) via mocked-import tests; add documentation map table to docs/index.md; mark frontend 80%+ target as achieved in TODO.md; iterative.py 97% -> 98%+, overall 76% -> 77%; 1472 backend tests pass (completed 2026-03-06)

- [Docs and Testing v55](exec-plans/completed/docs-and-testing-v55.md) --
  Frontend test coverage to 80%+: schedule CRUD operations (edit/delete/trigger/toggle with mocked API), task discovery from /tasks/current endpoint, task polling and poll error handling, notification banner render/dismiss/enable, toast display and close on terminal status, monitor resize/scroll handlers, New submission state reset; frontend coverage 71.5% -> 82.3% statements, 80.2% branches; 153 frontend tests pass (completed 2026-03-06)

- [Docs and Testing v54](exec-plans/completed/docs-and-testing-v54.md) --
  Frontend component test coverage expansion: form submission flow (POST payload validation, error handling, model/tools/skills inclusion, checkbox toggles, max iterations), monitor view (output tab switching Updates/Raw/Payload, task ID badge, status blinker, task inputs), schedule view (form rendering, field changes, cron preset dropdown, schedule creation API, Cancel button, Refresh, error handling); mockResponse helper with clone() support; frontend coverage 54% -> 71.5% statements, 81.2% branches; 134 frontend tests pass, 1470 backend tests pass (completed 2026-03-06)

- [Docs and Testing v53](exec-plans/completed/docs-and-testing-v53.md) --
  Branch coverage gap closure: base.py `_run_precommit_checks_and_fixes` stdout-only branch, `_finalize_repo_pr` pr_number delegation and empty default_branch fallback; registry.py `normalize_tool_selection` non-string ValueError and `format_tool_instructions_for_cli` tool-without-guidance skip; web.py `search_web` RelatedTopics non-list skip; goose.py line 135 dead code documented in tech-debt-tracker; registry.py 98% -> 99%, web.py 98% -> 99%; 1470 backend tests pass (completed 2026-03-06)

- [Docs and Testing v52](exec-plans/completed/docs-and-testing-v52.md) --
  Frontend test coverage expansion: utility edge cases (loadTaskHistory invalid JSON/non-array/empty taskId/limit enforcement, upsertTaskHistory empty/whitespace taskId/defaults, statusTone RECEIVED/RETRY/SCHEDULED/RESERVED/SENT/ERROR, cronFrequency hourly/minute-interval/empty fallbacks); component interaction tests (Hand world/Classic view toggle, schedule navigation, New submission return, Advanced settings expand, repo path/prompt/backend input changes, Clear button disabled); 110 frontend tests pass, 1464 backend tests pass (completed 2026-03-06)

- [Docs and Testing v51](exec-plans/completed/docs-and-testing-v51.md) --
  Backend test coverage gaps: iterative.py `_build_tree_snapshot` slash-only/multi-slash empty-parts edge cases (line 451); cli/base.py `stream()` producer_task cancellation path (lines 1047-1049); confirmed dead code items (iterative.py 830/858, codex.py 62) in tech-debt-tracker; QUALITY_SCORE.md updated; 1464 tests pass (completed 2026-03-06)


- [Docs and Testing v50](exec-plans/completed/docs-and-testing-v50.md) --
  Frontend test coverage expansion: export and test 11 pure utility functions (providerFromBackend, formatProviderName, repoName, cronFrequency, buildDeskSlots, checkDeskCollision, asRecord, readStringValue, readBoolishValue, readSkillsValue, backendDisplayName) with 55 new unit tests; add component-level render tests with @testing-library/react (8 tests); install @testing-library/dom peer dependency; 83 frontend tests pass, 1461 backend tests pass (completed 2026-03-06)

- [Docs and Testing v49](exec-plans/completed/docs-and-testing-v49.md) --
  MCP server `main()` stdio/http transport tests (97% -> 98%); CLI base IO loop interrupt break and process-exited-during-timeout break tests; `run()` CI-fix noop-emit callable test; PRODUCT_SENSE.md updated with implemented capabilities (scheduling, MCP, skills); QUALITY_SCORE.md updated; 1461 tests pass (completed 2026-03-06)

- [Docs and Testing v48](exec-plans/completed/docs-and-testing-v48.md) --
  Claude CLI `_skip_permissions_enabled` geteuid exception path, `_build_failure_message` instance delegation, `_StreamJsonEmitter` empty-line-between-events; Gemini CLI `_build_failure_message` instance delegation, `_invoke_gemini`/`_invoke_backend` async delegation; Goose CLI `_resolve_goose_provider_model_from_config` (7 tests), `_invoke_backend` delegation; QUALITY_SCORE.md updated; 1456 tests pass (completed 2026-03-06)

- [Docs and Testing v47](exec-plans/completed/docs-and-testing-v47.md) --
  Fix frontend localStorage.clear jsdom test failures (3 tests failing -> 0); add frontend tests for `apiUrl`, `isTerminalTaskStatus`, `parseError` edge cases (detail-missing/empty-body), additional `statusTone` coverage (14 -> 20 tests); document dead code in tech-debt-tracker (iterative.py lines 830/858, codex.py line 62); QUALITY_SCORE.md updated with frontend coverage; all tests pass (completed 2026-03-06)

- [Docs and Testing v46](exec-plans/completed/docs-and-testing-v46.md) --
  Codex `_build_failure_message` delegation and `_invoke_codex`/`_invoke_backend` async delegation (95% -> 98%); OpenCode `_invoke_opencode`/`_invoke_backend` async delegation (94% -> 100%); CLI base `_invoke_cli` delegation and `stream()` producer error re-raise; Atomic `stream()` `run_async` non-AssertionError exception re-raise; skills `_discover_catalog` missing dir early return (96% -> 98%); QUALITY_SCORE.md updated; 1440 tests pass (completed 2026-03-06)

- [Docs and Testing v45](exec-plans/completed/docs-and-testing-v45.md) --
  LangGraph/Atomic `stream()` pr_status elif branch coverage (entered/skipped for both satisfied and max-iterations paths); LangGraph `stream()` interrupted inner loop, non-chat-model event skip, empty text skip; Atomic `stream()` duplicate delta skip, awaitable empty delta skip; atomic.py `stream()` chat_message falsy branches (assertion fallback/async iter/awaitable); iterative.py 96% -> 97%; atomic.py 93% -> 97%; QUALITY_SCORE.md updated; 1430 tests pass (completed 2026-03-06)

- [Docs and Testing v44](exec-plans/completed/docs-and-testing-v44.md) --
  cli/base.py `stream()` CI fix message/pr_status paths; base.py `_finalize_repo_pr` native git auth and rich PR description; cli/base.py `_run_two_phase_inner` verbose mode; base.py 98% -> 99%; cli/base.py 97% -> 98%; QUALITY_SCORE.md updated; 1413 tests pass (completed 2026-03-06)

- [Docs and Testing v43](exec-plans/completed/docs-and-testing-v43.md) --
  celery_app.py coverage gaps (`_get_db_url_writer`, `ensure_usage_schedule`, `log_claude_usage` key paths including raw JWT and garbage output); ARCHITECTURE.md usage monitoring section; celery_app.py 73% -> 98%; QUALITY_SCORE.md updated; 1653 tests pass (completed 2026-03-06)

- [Docs and Testing v42](exec-plans/completed/docs-and-testing-v42.md) --
  `_build_tree_snapshot` empty-normalized/slash-only edge cases; `BasicLangGraphHand.run()` max_iterations status and pr_url; LangGraph/Atomic `stream()` pr_url yield at max iterations; `_effective_container_env_names` empty-blocked early return; iterative.py 94% -> 96%; QUALITY_SCORE.md updated; 1404 tests pass (completed 2026-03-06)

- [Docs and Testing v41](exec-plans/completed/docs-and-testing-v41.md) --
  Top-level `__version__` accessibility test; cli/main.py coverage gaps (docker-sandbox-claude backend branch, `_stream_hand` chunk printing/trailing newline, Python <3.12 atomic error, generic exception re-raise for non-CLI backends); SECURITY.md updated with Docker sandbox microVM isolation section; QUALITY_SCORE.md updated; 1397 tests pass (completed 2026-03-06)

- [Docs and Testing v40](exec-plans/completed/docs-and-testing-v40.md) --
  DockerSandboxClaudeCodeHand `_invoke_claude` (sandbox-wrapped cmd/result/raw fallback) and `_run_two_phase` (ensure+cleanup/skip-cleanup/cleanup-on-exception) tests; CLI base `_invoke_backend` delegation and `_run_two_phase` skill catalog lifecycle tests (staging/cleanup/cleanup-on-exception); BasicAtomicHand.stream() delta-without-prefix (assertion-fallback/async-iter/awaitable), file-change yield, tool-result yield tests; DESIGN.md updated with two-phase lifecycle and IO loop patterns; QUALITY_SCORE.md updated; 1391 tests pass (completed 2026-03-06)

- [Docs and Testing v39](exec-plans/completed/docs-and-testing-v39.md) --
  CLI hand `_invoke_cli_with_cmd` subprocess error path tests (FileNotFoundError with/without fallback, npx retry, stdout None, non-zero exit with/without retry, idle timeout, verbose mode); `BasicAtomicHand.run()` interrupted/max_iterations status paths; ARCHITECTURE.md updated with task result normalization and skill catalog sections; QUALITY_SCORE.md updated; 1378 tests pass (completed 2026-03-06)

- [Docs and Testing v38](exec-plans/completed/docs-and-testing-v38.md) --
  Package-level re-export tests for `cli/__init__.py` (7 symbols, identity checks), `meta/tools/__init__.py` (21 symbols, identity across 4 submodules), `meta/__init__.py` (`skills`/`tools` identity), `hands/v1/__init__.py` (10 symbols, identity with hand package); meta tools layer pattern added to DESIGN.md; `default_prompts.py`, `cli/__init__.py`, `meta/tools/__init__.py`, `meta/__init__.py`, `hands/v1/__init__.py` added to QUALITY_SCORE.md; 1365 tests pass (completed 2026-03-06)

- [Docs and Testing v37](exec-plans/completed/docs-and-testing-v37.md) --
  Package-level re-export tests for `hands/v1/hand/__init__.py` (`__all__` completeness, symbol identity, subprocess alias) and `ai_providers/__init__.py` (PROVIDERS dict, singleton identity, `__all__`); fix stale `obsidian/docs` reference in ARCHITECTURE.md; add `task_result.py`, `ai_providers/types.py`, `ai_providers/__init__.py`, `hands/v1/hand/__init__.py` to QUALITY_SCORE.md; 1319 tests pass (completed 2026-03-06)

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

- [2026-03-05 consolidated](exec-plans/completed/2026-03-05.md) —
  v5-v31: Pure helper, CLI hand, AI provider, iterative hand, Docker sandbox, celery, schedule, MCP server, web tool, PR description, and package-level test suites; provider abstraction design doc; ARCHITECTURE.md, DESIGN.md, SECURITY.md, RELIABILITY.md updates; 470 -> 1256 tests (completed 2026-03-05)
- [2026-03-04 consolidated](exec-plans/completed/2026-03-04.md) —
  v1-v4: Established docs structure, product specs, hand abstraction design doc, iterative hand tests, AI provider tests, two-phase CLI hands design doc, SECURITY.md sandboxing; 50 -> 470 tests (completed 2026-03-04)

## How plans work

1. Plans are created in `docs/exec-plans/active/` with a descriptive filename
2. Each plan has a status, creation date, tasks, and completion criteria
3. When all tasks are done, the plan moves to `docs/exec-plans/completed/`
4. The tech debt tracker (`docs/exec-plans/tech-debt-tracker.md`) captures
   ongoing technical debt items that don't warrant a full plan
