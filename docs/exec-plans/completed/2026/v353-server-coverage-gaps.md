# v353 — Server Module Coverage Gaps

**Created:** 2026-04-04
**Status:** Completed

## Goal

Close remaining coverage gaps in `server/app.py` (77% → 90%+) and
`server/schedules.py` (77% → 90%+) by testing route handlers with FastAPI
TestClient and ScheduleManager CRUD methods with mocked Redis. Push overall
project coverage from 95% toward 97%+.

## Tasks

- [x] Move completed v352 plan from `active/` to `completed/2026/`
- [x] Add ScheduleManager unit tests with mocked Redis/Celery:
      `validate_interval_seconds` (5 tests), `next_interval_run_time` (3 tests),
      chain nonce methods (8 tests), `_revoke_interval_chain` (4 tests),
      interval schedule CRUD (6 tests), `_create_redbeat_entry` body (1 test)
- [x] Add task workspace/diff/tree/file endpoint tests:
      `_resolve_task_workspace` (5 tests), task diff (2 tests),
      task tree (2 tests), task file content (3 tests) via TestClient
- [x] Add arcade (2 tests), multiplayer health (4 tests),
      `_schedule_to_response` (3 tests), grill endpoints (3 tests)
- [x] Run pytest, ruff check, ruff format — all clean
      (7919 passed, 8 skipped, 97.60% coverage)
- [x] Update INTENT.md, PLANS.md, Week-14 consolidation

## Completion criteria

- server/app.py coverage ≥ 90% ✓ (77% → 90%+)
- server/schedules.py coverage ≥ 90% ✓ (77% → 95%)
- Overall project coverage ≥ 97% ✓ (94.73% → 97.60%)
- All new tests pass ✓ (51 new tests, 7919 total pass)
- ruff check + format clean ✓
