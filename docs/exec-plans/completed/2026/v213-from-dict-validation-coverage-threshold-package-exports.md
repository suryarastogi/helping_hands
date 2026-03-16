# v213 — ScheduledTask.from_dict validation, coverage threshold, package exports

**Status:** Completed
**Created:** 2026-03-15
**Completed:** 2026-03-15

## Motivation

1. `ScheduledTask.from_dict()` checks for missing required keys but accepts empty/whitespace strings — e.g. `{"schedule_id": "", "name": " ", ...}` passes silently.
2. `validate_cron_expression()` doesn't strip leading/trailing whitespace, causing valid expressions with stray spaces to fail.
3. No `fail_under` coverage threshold prevents silent regressions in CI.
4. Package-level `__init__.py` files for `lib/`, `server/`, `cli/` have empty `__all__` — provides no public API surface for IDE autocomplete or `from pkg import *`.

## Tasks

- [x] Harden `ScheduledTask.from_dict()` to reject empty/whitespace required fields
- [x] Add `.strip()` to `validate_cron_expression()` input
- [x] Add `fail_under = 75` to `[tool.coverage.report]` in pyproject.toml
- [x] Populate `__all__` in `lib/__init__.py`, `server/__init__.py`, `cli/__init__.py`
- [x] Tests for all changes (28 new tests)
- [x] Verify lint, format, type checks pass

## Results

- **5189 passed, 217 skipped** (coverage 78.73%, threshold 75%)
- `ruff check` clean, `ruff format` clean, `ty check` clean
