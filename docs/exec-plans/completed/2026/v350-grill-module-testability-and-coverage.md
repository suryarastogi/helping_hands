# v350 — Grill Module Testability & Coverage

**Created:** 2026-04-04
**Status:** Active

## Goal

Fix 13 broken grill tests (celery import failure), make grill.py pure helper
functions testable without the server extra, and add comprehensive coverage for
`_build_system_prompt`, `_clone_repo`, `_summarize_tool_use`,
`_invoke_claude_turn`, and Redis helpers.

## Tasks

- [x] Move completed v349 plan from `active/` to `completed/2026/`
- [x] Fix INTENT.md broken link to v349 plan
- [x] Update PLANS.md: move v349 to completed section
- [x] Restructure `grill.py` to defer celery imports (lazy `try/except` block
      for the `@celery_app.task` decorator; `TYPE_CHECKING`-only `Task` import)
- [x] Extract `_grill_session_body` from the Celery task wrapper
- [x] Mark integration-only code (`_grill_session_body`, celery task wrapper)
      with `pragma: no cover`
- [x] Fix `test_grill.py`: remove broken top-level `pytest.importorskip("celery")`
      guard; import pure helpers directly
- [x] Add `TestRedisClient` tests: `_redis_client` env var usage (2 tests)
- [x] Add `TestRedisHelpers` tests: `_set_state`/`_get_state` round-trip,
      `_push_ai_msg`, `_pop_user_msg` (6 tests)
- [x] Add `TestBuildSystemPrompt` coverage: README fallback (.rst), truncation,
      large file tree, no README, reference repos, reference repo index failure,
      README OSError (7 new tests)
- [x] Add `TestCloneRepo` coverage: remote clone success, failure, timeout
      (3 new tests)
- [x] Add `TestSummarizeToolUse` edge cases: missing key, empty pattern (2 tests)
- [x] Add `TestInvokeClaudeTurn` coverage: first turn, resume, FileNotFoundError,
      non-zero exit, stdin OSError, text block concatenation, on_status callbacks,
      github_token env, malformed JSON, wait timeout, thinking dedup, tool_use
      reset, non-dict message/content, empty text block, duration-only result,
      empty stderr exit code, no-model flag, read-only tools (19 tests)
- [x] Add `TestInvokeClaudeTurnStreamError`: stdout iteration exception (1 test)
- [x] Fix GrillEnabled tests: add `pytest.importorskip("fastapi")` per-test
- [x] Fix all ruff lint violations (SIM117 nested with, RUF059 unused var)
- [x] Update tech debt tracker with grill session body coverage note

## Completion criteria

- 0 test failures (was 13 before)
- grill.py helper coverage ≥ 95% (was 4%)
- All new tests pass without celery/server extras installed
- ruff check + format clean
