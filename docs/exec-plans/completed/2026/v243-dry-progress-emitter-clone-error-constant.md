# v243 — DRY _ProgressEmitter and clone error constant

**Status:** completed
**Created:** 2026-03-16
**Completed:** 2026-03-16

## Motivation

`build_feature()` in `celery_app.py` calls `_update_progress()` 5 times (3 in
`build_feature` itself, 2 in `_collect_stream`) with ~20 nearly identical
keyword arguments repeated each time (~120 lines of boilerplate). Extracting a
`_ProgressEmitter` class that captures common arguments eliminates this
duplication.

Additionally, `"unknown git clone error"` appears as a bare string in both
`cli/main.py` and `celery_app.py`. Extracting to a shared constant in
`github_url.py` ensures consistency.

## Changes

### Code changes

- **Extracted `_ProgressEmitter` class** in `celery_app.py` — captures ~20
  common kwargs from `build_feature()` and exposes `emit(stage, **overrides)`
  method that delegates to `_update_progress()`
- **Refactored `_collect_stream` signature** — replaced ~18 individual kwargs
  with a single `emitter` parameter + `updates` list
- **Replaced 5 `_update_progress()` call sites** — 3 in `build_feature()` and
  2 in `_collect_stream()` now use `emitter.emit("starting")` /
  `emitter.emit("running", model=..., workspace=...)`
- **Extracted `DEFAULT_CLONE_ERROR_MSG`** to `github_url.py` — replaces bare
  `"unknown git clone error"` in `cli/main.py` and 2 bare strings in
  `celery_app.py` (`"unknown git clone error"` and `"unknown error"`)
- **Updated 4 `__all__` contract tests** — `test_github_url.py`,
  `test_v179_*.py`, `test_v210_*.py` now include `DEFAULT_CLONE_ERROR_MSG`
- **Updated 4 existing `_collect_stream` tests** in `test_celery_app.py` to
  use new emitter-based signature

### Tasks completed

- [x] Implement `_ProgressEmitter` class in celery_app.py
- [x] Refactor `_collect_stream` signature to accept emitter
- [x] Replace 5 `_update_progress()` call sites with `emitter.emit()`
- [x] Extract `DEFAULT_CLONE_ERROR_MSG` to github_url.py
- [x] Use constant in cli/main.py and celery_app.py
- [x] Add tests for `_ProgressEmitter` (12 tests)
- [x] Add tests for `DEFAULT_CLONE_ERROR_MSG` (7 tests)
- [x] Add `_collect_stream` signature tests (3 tests)
- [x] Update PLANS.md

## Test results

- 22 new tests added (all passed)
- 5773 passed, 241 skipped (no regressions)
- All lint/format checks pass

## Completion criteria

- [x] All tasks checked
- [x] `uv run pytest` passes with no new failures
- [x] `uv run ruff check .` passes
- [x] `uv run ruff format --check .` passes
