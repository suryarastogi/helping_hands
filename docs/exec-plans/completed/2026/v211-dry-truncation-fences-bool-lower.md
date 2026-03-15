# v211 — DRY truncation suffix, code fences, and bool-lower helper

**Status:** Completed
**Created:** 2026-03-15

## Summary

Three self-contained DRY improvements in `iterative.py`:

1. **`_TRUNCATION_SUFFIX` constant + `_truncation_note()` helper** — Extract the
   repeated `"\n[truncated]" if truncated else ""` pattern (6 occurrences) into a
   module-level constant and a staticmethod.

2. **Code fence constants** — Extract `_FENCE_TEXT`, `_FENCE_JSON`, and `_FENCE_CLOSE`
   constants for the repeated `` ```text ``, `` ```json ``, and `` ``` `` markers
   used in tool result formatting (7+ occurrences).

3. **`_bool_lower()` staticmethod** — Extract the repeated `str(bool_val).lower()`
   pattern (4 occurrences) into a named helper for clarity and consistency.

4. **Versioned tests** — Add `tests/test_v211_dry_truncation_fences_bool_lower.py`
   with 31 tests verifying the new constants, helpers, and absence of inline duplicates.

## Tasks

- [x] Extract `_TRUNCATION_SUFFIX` constant and `_truncation_note()` staticmethod
- [x] Extract `_FENCE_TEXT`, `_FENCE_JSON`, and `_FENCE_CLOSE` constants
- [x] Extract `_bool_lower()` staticmethod
- [x] Replace all inline occurrences with the new constants/helpers
- [x] Add versioned tests (31 tests)
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
- 5174 passed, 216 skipped
