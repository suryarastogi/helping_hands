# v214 — ScheduleManager unit tests

**Status:** Completed
**Created:** 2026-03-15
**Completed:** 2026-03-15

## Motivation

1. `ScheduleManager` class in `server/schedules.py` had 0% test coverage — all CRUD methods (create, update, delete, enable, disable, get, list, record_run, trigger_now) and internal helpers (_save_meta, _load_meta, _delete_meta, _list_meta_keys, _meta_key, _create_redbeat_entry, _delete_redbeat_entry) were untested.

## Tasks

- [x] Add ScheduleManager unit tests with mocked Redis/Celery/RedBeat (50 tests)
- [x] Verify lint, format, type checks, and tests pass
- [x] Update docs (PLANS.md, Week-12)

## Results

- **6078 passed, 2 skipped** (coverage 98.27%, threshold 75%)
- `schedules.py` coverage: 0% → 97%
- `ruff check` clean, `ruff format` clean
- E501 line-length violations confirmed as informational only (in `ignore` list)
