# Tech Debt Tracker

Tracking technical debt items for prioritization and resolution.

## Active Items

| ID | Area | Description | Priority | Added |
|----|------|-------------|----------|-------|
| TD-004 | Testing | `default_prompts.py` has no regression tests | Low | 2026-03-04 |
| TD-005 | Docs | `docs/generated/db-schema.md` not yet generated from actual schema | Low | 2026-03-04 |
| TD-006 | Testing | `celery_app.py` task bodies and retry logic have low coverage | Medium | 2026-03-04 |

## Resolved Items

| ID | Area | Description | Resolved | Notes |
|----|------|-------------|----------|-------|
| TD-001 | Testing | `ScheduleManager` class entirely untested (~270 lines) | 2026-03-04 | Added 18 unit tests covering CRUD, enable/disable, record_run, trigger_now |
| TD-002 | Testing | `registry.py` parser functions have minimal edge-case coverage | 2026-03-04 | Added 26 edge-case tests for parsers, normalizer, and runner validation |
| TD-003 | Testing | AI provider error paths not covered | 2026-03-04 | Added tests for lazy init, model override, acomplete, ImportError, install hints |
| — | Testing | `filesystem.py` had no dedicated tests | 2026-03-04 | Added comprehensive path safety tests |
