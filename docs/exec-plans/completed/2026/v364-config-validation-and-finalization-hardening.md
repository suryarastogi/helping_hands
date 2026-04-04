# v364 — Config Validation & Finalization Error Hardening

**Status:** Completed
**Created:** 2026-04-04

## Goal

Harden two critical paths:

1. **Config validation** — Validate `repo` format early in `Config.from_env()` to
   reject clearly invalid inputs (empty, whitespace-only, path traversal) before
   they reach backend dispatch. Warn when `model` remains at its default sentinel.

2. **Finalization error handling** — Add catch-all exception handling in
   `_finalize_repo_pr()` and broaden exception types caught during push to
   prevent unexpected errors from propagating as unhandled crashes.

## Tasks

- [x] Create active plan
- [x] Add `validate_repo_value` helper in `validation.py` and call from `Config.from_env()`
- [x] Add model-default debug warning in `Config.from_env()`
- [x] Add catch-all `except Exception` in `_finalize_repo_pr()` (logged at ERROR)
- [x] Broaden push exception handling from `RuntimeError` to `(RuntimeError, OSError)`
- [x] Write 14 tests for `validate_repo_value` (empty, whitespace, null, newline, traversal, valid)
- [x] Write 9 tests for config repo validation and model warning in `test_config.py`
- [x] Write 3 tests for finalization catch-all and push OSError fallback
- [x] Update existing tests (validation __all__, finalize log message, AST narrowing tests)
- [x] Verify all tests pass (`uv run pytest -v`)
- [x] Update PLANS.md, INTENT.md, move plan to completed

## Results

- 24 new tests across 3 files, all passing
- 4 existing tests updated (validation __all__, finalize logging, AST narrowing)
- Coverage 76.05% → 76.15%
- 6854 tests pass, 0 failures
- Lint and format clean

## Completion criteria

- [x] All new tests pass
- [x] No regressions in existing tests
- [x] Coverage maintained or improved (76.05% → 76.15%)
- [x] PLANS.md updated
