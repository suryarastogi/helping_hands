# v338 — Server App & Celery Pure Function Coverage

**Status:** completed
**Created:** 2026-03-29

## Goal

Cover remaining uncovered branches in `server/app.py` and
`server/celery_app.py` pure helper functions. Most helpers were already tested
but specific branches had gaps: `_is_recently_terminal` (all branches),
`_upsert_current_task` edge cases, `_update_progress` issue_number branch,
`_sync_issue_status` failed-without-error branch, and `ensure_usage_schedule`
OSError catch.

## Tasks

- [x] Move v337 from active to completed, update PLANS.md
- [x] Add `_is_recently_terminal` tests: non-terminal status, FAILURE with
  `failed` timestamp, SUCCESS with `succeeded` timestamp, fallback to
  `timestamp`, old timestamp, missing timestamp, non-numeric timestamp,
  REVOKED with timestamp
- [x] Add `_upsert_current_task` edge case tests: empty source skip,
  fill-missing-backend, preserve-existing-backend
- [x] Add `_update_progress` issue_number tests: included when set,
  absent when None
- [x] Add `_sync_issue_status` test: failed without error omits error line
- [x] Add `ensure_usage_schedule` OSError test: Redis-unavailable swallowed
- [x] Run full test suite, verify ≥75% coverage and 0 failures
- [x] Update INTENT.md, PLANS.md, daily consolidation, Week-13

## Results

- **app.py (1% → 80%):** 12 new tests — 9 `_is_recently_terminal` (all
  branches), 3 `_upsert_current_task` edge cases. Note: most coverage gain
  is from installing `--extra server` dependencies enabling existing tests
- **celery_app.py (3% → 99%):** 4 new tests — 2 `_update_progress`
  issue_number, 1 `_sync_issue_status` failed-without-error, 1
  `ensure_usage_schedule` OSError
- 7656 backend tests passed, 0 failures, 96.45% coverage ✓
- Docs updated ✓

## Completion criteria

- All uncovered branches in `_is_recently_terminal` covered ✓
- `_upsert_current_task` empty-source and fill-missing edge cases covered ✓
- `_update_progress` issue_number branch covered ✓
- `_sync_issue_status` failed-without-error branch covered ✓
- `ensure_usage_schedule` OSError catch covered ✓
- All existing tests still pass ✓ (7656 passed)
- Docs updated ✓
