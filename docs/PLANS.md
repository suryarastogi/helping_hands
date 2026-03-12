# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [2026-03-12 v136](exec-plans/completed/2026-03-12.md) --
  Gitignore E2E artifacts, base.py/cli/base.py constant extraction, _truncate_summary limit validation; 10 tests

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
  v104-v131: Dead code cleanup, server routing, E2E draft PR, Celery helpers, health checks, ty in CI, Claude CLI emitter hardening, Hand World factory theme, input validation, DRY validators, assert→RuntimeError guards, debug logging, MCP validation, tool summarization expansion, git operation hardening, type safety, timeout bounds, boilerplate line test coverage, robustness hardening, exception debug logging, Goose env test coverage, defensive CI response handling, frontend form validation, network error handling; 3031 -> 3329 passing tests (backend), 153 -> 178 tests (frontend)
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
