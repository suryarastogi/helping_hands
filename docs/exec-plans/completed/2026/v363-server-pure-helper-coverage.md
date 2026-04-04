# v363 — Server Pure Helper Coverage

**Status:** Completed
**Created:** 2026-04-04

## Goal

Close unit-test coverage gaps in the three server modules (`app.py`, `celery_app.py`,
`schedules.py`) by testing their **pure helper functions** — no running server,
Redis, or Celery infrastructure required.

These three modules accounted for ~1,725 of 1,731 total uncovered statements.

## Tasks

- [x] Write `tests/test_server_app_task_helpers.py` — 71 tests for app.py task extraction, status normalization, source merging, env config, kwargs parsing, usage extraction, backend parsing
- [x] Write `tests/test_celery_app_helpers.py` — 20 tests for celery_app.py `_normalize_backend`, `_format_runtime`, `_resolve_repo_path` edge cases
- [x] Write `tests/test_schedules_helpers.py` — 20 tests for schedules.py validation, next-run-time, schedule ID generation
- [x] Verify all tests pass and coverage improves
- [x] Update PLANS.md, INTENT.md, and move plan to completed

## Results

- 111 new tests across 3 files, all passing
- With server extras installed: app.py 1%→94%, celery_app.py 3%→99%, schedules.py 2%→95%
- Total coverage with server extras: 98.71% (8100 tests pass)
- Without server extras: 76.05% (6830 tests pass, 0 failures, server tests skip)

## Completion criteria

- [x] All new tests pass (`uv run pytest -v`)
- [x] Coverage improves toward 80%+ overall (98.71% with server extras)
- [x] No regressions in existing tests
- [x] PLANS.md updated with active plan reference
