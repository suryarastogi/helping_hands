# v356 — Server App Endpoint Coverage Hardening

**Created:** 2026-04-04
**Status:** Active

## Goal

Close coverage gaps in `server/app.py` (90% → 95%+) by testing uncovered
branches in task diff parsing, file tree building, file content reading, and
helper functions. These are the largest remaining coverage gaps in the codebase
(94 uncovered lines).

## Tasks

- [x] Add diff edge-case tests: git-diff-HEAD failure fallback, multi-file diff
      with added/deleted/renamed status, untracked files as added, timeout/OSError
- [x] Add file tree edge-case tests: git status rename/delete parsing, parent
      dir insertion, PermissionError fallback, short status line skip
- [x] Add file content edge-case tests: path traversal rejection, large file
      rejection, OS error, diff status detection (new/deleted file), untracked
      file detection, git diff timeout
- [x] Add `_extract_task_kwargs` test: request.kwargs as string branch,
      request.kwargs as dict, invalid JSON fallback
- [x] Move completed v355 plan to completed/2026/
- [x] Update `INTENT.md`, `docs/PLANS.md`
- [x] Run pytest, ruff check, ruff format — all clean
      (7971 passed, 8 skipped, 98.70% coverage)

## Completion criteria

- `server/app.py` coverage ≥95% (from 90%) ✓ (95%)
- All existing tests still pass ✓ (7971 passed)
- ruff check + format clean ✓
