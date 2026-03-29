# v336 — Server Module Coverage Hardening

**Status:** completed
**Created:** 2026-03-29

## Goal

Close testable coverage gaps in `server/app.py` (1% → ~78%),
`server/celery_app.py` (3% → ~99%), and `server/schedules.py` (3% → ~98%)
by testing pure helper functions that don't require live Redis/Celery/FastAPI.
Target: overall backend coverage 75.84% → 96%.

## Tasks

- [x] Move completed v335 to `completed/2026/`, create 2026-03-29 daily consolidation
- [x] Add app.py pure helper tests: `_extract_nested_str_field`, `_merge_source_tags`, `_is_recently_terminal`, `_iter_worker_task_entries`, `_safe_inspect_call`, `_first_validation_error_msg`, `_is_running_in_docker`
- [x] Add celery_app.py tests: `_ProgressEmitter`, `_maybe_persist_pr_to_schedule`, `_try_create_issue`, `_sync_issue_started`, `_sync_issue_status`, `_sync_issue_completed`, `_sync_issue_failed`, `_try_add_to_project`, `_get_db_url_writer`
- [x] Add schedules.py tests: `_check_optional_dep`, `get_schedule_manager`
- [x] Run full test suite, verify coverage improvement
- [x] Update INTENT.md, PLANS.md, QUALITY_SCORE.md

## Results

- 35 new app.py tests in `test_server_app_task_helpers.py`: task listing helpers,
  terminal state detection, worker entry flattening, validation error extraction,
  Docker detection
- 31 new celery_app.py tests in `test_celery_app_coverage.py`: ProgressEmitter,
  PR schedule persistence, issue lifecycle sync (create/started/status/completed/failed),
  project board integration, DB URL resolution
- 6 new schedules.py tests in `test_schedules_coverage.py`: dependency check helper,
  schedule manager factory
- server/app.py: 1% → 78% coverage
- server/celery_app.py: 3% → 99% coverage
- server/schedules.py: 3% → 98% coverage
- Overall: 75.84% → 96% (with server extras installed)
- 7676 backend tests passed (72 new), 0 new failures
- Pre-existing Keychain/OAuth test failures (16) unrelated to this change

## Completion criteria

- All new tests pass ✓ (72 new tests)
- Overall coverage ≥ 77% ✓ (96%)
- server/app.py, celery_app.py measurably improved ✓
- Docs updated ✓
