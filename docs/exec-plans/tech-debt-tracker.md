# Tech Debt Tracker

Tracking technical debt items for prioritization and resolution.

## Active Items

| ID | Area | Description | Priority | Added |
|----|------|-------------|----------|-------|
| TD-001 | Testing | `ScheduleManager` class entirely untested (~270 lines) | Medium | 2026-03-04 |
| TD-002 | Testing | `registry.py` parser functions have minimal edge-case coverage | Medium | 2026-03-04 |
| TD-003 | Testing | AI provider error paths not covered (ImportError, invalid keys) | Medium | 2026-03-04 |
| TD-004 | Testing | `default_prompts.py` has no regression tests | Low | 2026-03-04 |
| TD-005 | Docs | `docs/generated/db-schema.md` not yet generated from actual schema | Low | 2026-03-04 |
| TD-006 | Testing | `celery_app.py` task bodies and retry logic have low coverage | Medium | 2026-03-04 |

## Resolved Items

| ID | Area | Description | Resolved | Notes |
|----|------|-------------|----------|-------|
| — | Testing | `filesystem.py` had no dedicated tests | 2026-03-04 | Added comprehensive path safety tests |
