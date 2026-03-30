# v342 — Server Helper Coverage & Weekly Consolidation

**Status:** Completed
**Created:** 2026-03-30

## Scope

Close remaining untested pure/helper functions in server modules and consolidate
weekly documentation.

## Tasks

- [x] Add tests for `_maybe_persist_pr_to_schedule` in `celery_app.py` (6 tests)
- [x] Add tests for `_validate_path_param` in `app.py` (3 tests)
- [x] Add tests for `_is_running_in_docker` in `app.py` (3 tests)
- [x] Update INTENT.md and PLANS.md

## Completion criteria

All tests pass, coverage does not regress, PLANS.md and INTENT.md updated.

## Results

12 new tests added in `test_v342_server_helper_coverage.py`. `celery_app.py`
coverage 99% (was 3% without server extras). All 7738 tests pass, 96.62% coverage.
