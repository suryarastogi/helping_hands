# v234 — DEFAULT_REDIS_URL constant, health check & DB exception narrowing

**Created:** 2026-03-16
**Status:** Completed

## Goal

Three self-contained improvements across server modules:

1. **Extract `DEFAULT_REDIS_URL` constant** — `"redis://localhost:6379/0"` is duplicated
   in `celery_app.py` (`_resolve_celery_urls`) and `app.py` (`_check_redis_health`).
   Move to `server/constants.py` and reference from both sites.
2. **Narrow health check `except Exception` handlers** in `app.py`:
   - `_check_redis_health`: split `ImportError` from `redis.RedisError` + `OSError`
   - `_check_db_health`: split `ImportError` from `psycopg2.Error` + `OSError`
3. **Narrow `except Exception` handlers** in `celery_app.py`:
   - `log_claude_usage` DB write: split `ImportError` from `psycopg2.Error` + `OSError`
   - `ensure_usage_schedule`: catch `(ImportError, OSError)` instead of bare `Exception`

## Tasks

- [x] Create this plan
- [x] Add `DEFAULT_REDIS_URL` to constants.py and update `__all__`
- [x] Replace hardcoded Redis URL in `celery_app.py`
- [x] Replace hardcoded Redis URL in `app.py`
- [x] Narrow `_check_redis_health` exception handler
- [x] Narrow `_check_db_health` exception handler
- [x] Narrow `log_claude_usage` DB write exception handler
- [x] Narrow `ensure_usage_schedule` exception handler
- [x] Add tests (22 new: all passed)
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All changes have tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/server/constants.py` — new `DEFAULT_REDIS_URL` constant + `__all__` update
- `src/helping_hands/server/app.py` — use `_DEFAULT_REDIS_URL`, narrow health check exceptions
- `src/helping_hands/server/celery_app.py` — use `_DEFAULT_REDIS_URL`, narrow DB write + schedule exceptions
- `tests/test_v234_redis_url_constant_health_check_exception_narrowing.py` — 22 new AST + runtime tests
- `tests/test_server_app_helpers.py` — fix mock modules for narrowed except clauses
- `tests/test_celery_app.py` — fix mock psycopg2 for narrowed except clause
- `tests/test_v233_response_status_constants_exception_narrowing.py` — tighten bare Exception count to 0
- `tests/test_v232_redbeat_constants_exception_narrowing.py` — search by handler type instead of index
