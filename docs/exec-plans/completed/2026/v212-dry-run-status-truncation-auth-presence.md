# v212 — DRY run-status strings, truncation marker, auth-presence labels

**Status:** Completed
**Created:** 2026-03-15

## Summary

Extract repeated inline string literals in `iterative.py` to module-level
constants, improving maintainability and reducing risk of typo-induced bugs.

1. **`_RUN_STATUS_INTERRUPTED` / `_RUN_STATUS_SATISFIED` / `_RUN_STATUS_MAX_ITERATIONS`**
   — Extract the three run-status strings used identically in both
   `BasicLangGraphHand.run()` and `BasicAtomicHand.run()` status assignment blocks.

2. **`_TRUNCATION_MARKER`** — Extract the repeated `"\n[truncated]"` string used
   in `_format_command_result()`, `_format_web_search_result()`,
   `_format_web_browse_result()`, and `_execute_read_requests()`.

3. **`_AUTH_PRESENT_LABEL` / `_AUTH_ABSENT_LABEL`** — Extract `"set"` / `"not set"`
   auth-presence indicator strings used in both `stream()` methods.

4. **Tests** — Versioned test file verifying constant values, types, and
   source-level usage in the module.

## Tasks

- [x] Extract `_RUN_STATUS_*` constants
- [x] Extract `_TRUNCATION_MARKER` constant
- [x] Extract `_AUTH_PRESENT_LABEL` / `_AUTH_ABSENT_LABEL` constants
- [x] Add `tests/test_v212_dry_run_status_truncation_auth.py`
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
- 5189 passed, 216 skipped
