# v215 — Server Schedule Endpoint Tests

**Status:** Completed
**Completed:** 2026-03-15
**Created:** 2026-03-15
**Goal:** Cover the 8 uncovered schedule endpoint functions and remaining
uncovered lines in server/app.py, pushing coverage from 89% toward 95%+.

## Context

`server/app.py` has 79 uncovered statements, mostly in the schedule endpoint
handler functions (lines 3829-3993) plus a few isolated gaps (form validation
error path, `/config`, `/notif-sw.js`, enqueue_build endpoint, and some
branch partials in `_fetch_flower_current_tasks`). The schedule endpoints all
follow the same pattern: call `_get_schedule_manager()` then delegate.

## Tasks

- [x] Create test file `tests/test_v215_schedule_endpoints.py`
  - Test `_get_schedule_manager()` singleton + ImportError path
  - Test `get_cron_presets()` endpoint
  - Test `list_schedules()` endpoint
  - Test `create_schedule()` endpoint (success + ValidationError)
  - Test `get_schedule()` endpoint (found + 404)
  - Test `update_schedule()` endpoint (success + 404 + redacted token)
  - Test `delete_schedule()` endpoint (success + 404)
  - Test `enable_schedule()` / `disable_schedule()` (success + 404)
  - Test `trigger_schedule()` (success + 404)
  - Test `notif_sw()` returns JS
  - Test `get_server_config()` endpoint
  - Test `enqueue_build()` endpoint
  - Test form submission ValidationError redirect path
- [x] Run tests, verify coverage improvement
- [x] Update PLANS.md and move plan to completed

## Completion criteria

- All new tests pass
- `server/app.py` coverage ≥ 94%
- No lint/format regressions
