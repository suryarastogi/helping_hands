# v255: Consolidate imports, extract magic numbers

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

1. **Verbose single-item imports:** `celery_app.py` and `app.py` each had 16-25
   individual `from X import Y as _Y` statements from the same module
   (`server.constants`, `github_url`, `factory`), consuming excessive vertical
   space and hurting readability. Root cause: ruff's isort splits `as`-aliased
   imports into separate statements by default.

2. **Magic numbers:** `celery_app.py` contained hardcoded numeric values
   (2000/200/4000/800/40/180) for progress update limits without named constants.

## Tasks

- [x] Enable `combine-as-imports = true` in ruff isort config (pyproject.toml)
- [x] Consolidate `server.constants` imports in `celery_app.py` (16 → 1 statement)
- [x] Consolidate `github_url` imports in `celery_app.py` (6 → 1 statement)
- [x] Consolidate `factory` imports in `celery_app.py` (2 → 1 statement)
- [x] Consolidate `server.constants` imports in `app.py` (25 → 1 statement)
- [x] Extract 6 magic number constants: `_MAX_UPDATES_VERBOSE` (2000),
  `_MAX_UPDATES_NORMAL` (200), `_MAX_LINE_CHARS_VERBOSE` (4000),
  `_MAX_LINE_CHARS_NORMAL` (800), `_FLUSH_CHARS_VERBOSE` (40),
  `_FLUSH_CHARS_NORMAL` (180)
- [x] Run ruff --fix across codebase with new config (21 files auto-fixed)
- [x] Add `tests/test_v255_consolidated_imports_magic_numbers.py` (12 tests)
- [x] Run full test suite: 5972 passed, 270 skipped

## Completion criteria

- All `as`-aliased imports from same module consolidated into single statement
- All magic numbers have named constants with docstrings
- All existing tests pass (5972 passed, 270 skipped)
- New tests verify source consistency via AST parsing
