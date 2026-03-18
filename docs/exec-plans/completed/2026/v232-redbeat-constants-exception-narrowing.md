# v232 — RedBeat prefix constants, task name constants, exception narrowing

**Created:** 2026-03-16
**Status:** Completed

## Goal

Three self-contained DRY/safety improvements across server modules:

1. **Extract RedBeat prefix constants** — `REDBEAT_KEY_PREFIX`,
   `REDBEAT_SCHEDULE_ENTRY_PREFIX`, and `REDBEAT_USAGE_ENTRY_NAME` to
   `server/constants.py`, replacing scattered string literals in
   `celery_app.py` and `schedules.py`.
2. **Extract Celery task name constants** — `TASK_NAME_SCHEDULED_BUILD` and
   `TASK_NAME_LOG_USAGE` to `server/constants.py`, replacing bare strings
   in `@celery_app.task` decorators and RedBeat entry registrations.
3. **Narrow `except Exception` → `except KeyError`** in `ensure_usage_schedule()`
   — consistent with `schedules.py:471` pattern for RedBeat entry-not-found.

## Tasks

- [x] Create this plan
- [x] Extract `REDBEAT_KEY_PREFIX`, `REDBEAT_SCHEDULE_ENTRY_PREFIX`, `REDBEAT_USAGE_ENTRY_NAME`
- [x] Extract `TASK_NAME_SCHEDULED_BUILD`, `TASK_NAME_LOG_USAGE`
- [x] Narrow `except Exception` → `except KeyError` in `ensure_usage_schedule()`
- [x] Add tests (20 new: 19 passed, 1 skipped without celery)
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All changes have tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/server/constants.py` — 5 new constants + `__all__` update
- `src/helping_hands/server/celery_app.py` — use shared constants, narrow KeyError
- `src/helping_hands/server/schedules.py` — use shared constants
- `tests/test_v232_redbeat_constants_exception_narrowing.py` — 20 new tests
- `tests/test_v197_dry_field_bounds_backend_type_bytes_per_mb.py` — `__all__` superset check
- `tests/test_v196_dry_defaults_reference_repos_cache_ttl.py` — `__all__` superset check
- `tests/test_v179_dry_github_url_server_constants.py` — `__all__` superset check
