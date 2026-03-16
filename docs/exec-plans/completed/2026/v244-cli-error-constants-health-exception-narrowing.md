# v244 — CLI error constants and health check exception narrowing

**Status:** completed
**Created:** 2026-03-16
**Completed:** 2026-03-16

## Motivation

`cli/main.py` contains bare string literals for model-not-found error
detection (`"model_not_found"`, `"does not exist"`) and an inline backend
set for error-exit decisions. Extracting these to module-level constants
improves readability and testability.

`server/app.py` still has two `except Exception` handlers in
`_check_workers_health()` and `_resolve_worker_capacity()` that can be
narrowed to specific Celery/connection exception types.

## Changes

### Code changes

- **Extracted `_MODEL_NOT_FOUND_MARKERS`** tuple in cli/main.py — replaces
  bare `"model_not_found"` and `"does not exist"` string comparisons with
  `any(marker in msg for marker in _MODEL_NOT_FOUND_MARKERS)`
- **Extracted `_MODEL_NOT_AVAILABLE_MSG`** template in cli/main.py —
  replaces inline f-string with `.format(model=...)` call
- **Extracted `_CLI_ERROR_EXIT_BACKENDS`** frozenset in cli/main.py —
  replaces inline `{...}` set literal in `main()` error handling
- **Narrowed `_check_workers_health()`** exception handler from
  `except Exception` to `except (ConnectionError, OSError, TimeoutError)`
- **Narrowed `_resolve_worker_capacity()`** exception handler from
  `except Exception` to `except (ConnectionError, OSError, TimeoutError)`
- **Updated existing tests** in `test_v237_remaining_exception_narrowing.py`,
  `test_v116_exception_logging.py`, and `test_server_app_helpers.py` to
  match narrowed exception types

### Tasks completed

- [x] Extract `_MODEL_NOT_FOUND_MARKERS` tuple in cli/main.py
- [x] Extract `_MODEL_NOT_AVAILABLE_MSG` template in cli/main.py
- [x] Extract `_CLI_ERROR_EXIT_BACKENDS` frozenset in cli/main.py
- [x] Narrow `except Exception` in `_check_workers_health()` to specific types
- [x] Narrow `except Exception` in `_resolve_worker_capacity()` to specific types
- [x] Add tests for model-not-found markers (8 tests)
- [x] Add tests for CLI error-exit backends set (6 tests)
- [x] Add tests for narrowed exception handlers (7 tests: 2 AST + 5 runtime)
- [x] Update PLANS.md

## Test results

- 21 new tests added (18 passed, 5 skipped without fastapi, 2 AST-based)
- 5792 passed, 246 skipped (no regressions)
- All lint/format checks pass

## Completion criteria

- [x] All tasks checked
- [x] `uv run pytest` passes with no new failures
- [x] `uv run ruff check .` passes
- [x] `uv run ruff format --check .` passes
