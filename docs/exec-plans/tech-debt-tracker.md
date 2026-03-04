# Tech Debt Tracker

Tracking technical debt items for prioritization and resolution.

## Active Items

| ID | Area | Description | Priority | Added |
|----|------|-------------|----------|-------|
| TD-003 | Testing | AI provider error paths not covered (ImportError, invalid keys) | Medium | 2026-03-04 |
| TD-005 | Docs | `docs/generated/db-schema.md` not yet generated from actual schema | Low | 2026-03-04 |
| TD-006 | Testing | `celery_app.py` task bodies and retry logic have low coverage | Medium | 2026-03-04 |
| TD-007 | Testing | `test_schedules.py` was missing `pytest.importorskip("celery")` guard | Low | 2026-03-04 |

## Resolved Items

| ID | Area | Description | Resolved | Notes |
|----|------|-------------|----------|-------|
| — | Testing | `filesystem.py` had no dedicated tests | 2026-03-04 | Added comprehensive path safety tests |
| TD-001 | Testing | `ScheduleManager` class entirely untested (~270 lines) | 2026-03-04 | Added `test_schedule_manager.py` with mocked Redis — CRUD, enable/disable, record_run |
| TD-002 | Testing | `registry.py` parser functions have minimal edge-case coverage | 2026-03-04 | Added 25+ edge-case tests for validators, normalize, validate, merge |
| TD-004 | Testing | `default_prompts.py` has no regression tests | 2026-03-04 | Resolved in v1 plan |
| TD-007 | Testing | `test_schedules.py` missing importorskip guard | 2026-03-04 | Fixed — was causing collection error without celery |
