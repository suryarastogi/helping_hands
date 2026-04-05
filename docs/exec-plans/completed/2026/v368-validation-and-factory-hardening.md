# v368 — Validation & Factory Hardening

**Created:** 2026-04-05
**Status:** Completed
**Theme:** Add missing boundary validation and module-level consistency checks

## Context

Two defensive gaps found during code review:

1. `validate_repo_value()` in `validation.py` accepts a `str` type hint but has
   no `isinstance` guard. Non-string input (e.g. `None`, `int`) raises
   `AttributeError` on `.strip()` instead of a clear `TypeError`. Every other
   validation function in the module (`require_non_empty_string`,
   `require_positive_int`, `require_positive_float`) already validates types.

2. `factory.py` defines `SUPPORTED_BACKENDS` (frozenset) and
   `_BACKEND_ENABLED_ENV_VARS` (dict) separately with no consistency check. If a
   future backend is added to one but not the other, `get_enabled_backends()`
   silently returns wrong results. A module-level assertion catches this at
   import time.

## Tasks

- [x] Add `isinstance` type guard to `validate_repo_value()` raising `TypeError`
- [x] Add module-level assertion in `factory.py` verifying backend/env-var consistency
- [x] Add tests for `validate_repo_value()` type guard (int, None, list, bool — 4 tests)
- [x] Add tests for factory consistency (import succeeds, sets match, env-var values — 3 tests)
- [x] Update docs (PLANS.md, INTENT.md, Week-14)

## Completion criteria

- `validate_repo_value(123)` raises `TypeError`, not `AttributeError`
- Factory import-time check catches SUPPORTED_BACKENDS / env-var mismatch
- All existing tests still pass
