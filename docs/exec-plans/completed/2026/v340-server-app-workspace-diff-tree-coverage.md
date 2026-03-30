# v340 — Server App Workspace, Diff, Tree & Worker Capacity Coverage

**Status:** Completed
**Created:** 2026-03-30
**Theme:** Close coverage gaps in `server/app.py` workspace/diff/tree endpoints and worker capacity resolution

## Goal

Raise `server/app.py` coverage from 80% to 97%+ by testing the workspace resolution pipeline, diff/tree/file endpoints, worker capacity cascade, arcade scores, and multiplayer health endpoints.

## Tasks

- [x] Test `_resolve_worker_capacity` — celery stats path, env var path, default path
- [x] Test `_resolve_task_workspace` — dict result, no workspace, cleaned up, not found
- [x] Test `_build_task_diff` — diff parsing, untracked files, git error, empty diff
- [x] Test `_build_task_tree` — tree walk, git status annotations, max entries, permission error
- [x] Test `_read_task_file` — content read, path traversal, too large, untracked file diff
- [x] Test arcade endpoints — get/post high scores
- [x] Test multiplayer health endpoints
- [x] Run full test suite, verify coverage improvement

## Completion criteria

- [x] All new tests pass — 50 passed, 0 failures
- [x] No regressions in existing tests — 7753 passed
- [x] `server/app.py` coverage ≥ 95% — achieved 97%
- [x] Overall coverage remains above 75% — achieved 99.13%

## Results

- **50 new tests** in `test_v340_server_app_workspace_diff_tree.py`
- `server/app.py` coverage: 80% → 97% (+17 percentage points)
- Overall coverage: 96.45% → 99.13%
- 7753 tests passed, 0 failures, 8 skipped
