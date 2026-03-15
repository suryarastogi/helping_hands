# v213 — Public API cleanup, __all__ hygiene, coverage gaps

**Status:** Completed
**Created:** 2026-03-15

## Summary

Promote cross-module private helpers to public API, clean up `__all__` exports,
and close small coverage gaps in goose.py and codex.py.

1. **Promote registry.py payload validators to public API** — `_parse_str_list`,
   `_parse_positive_int`, `_parse_optional_str` renamed to `parse_str_list`,
   `parse_positive_int`, `parse_optional_str` and added to `__all__`. Updated
   all import sites (iterative.py, test files).

2. **Remove `_TwoPhaseCLIHand` from `cli/__init__.py`** — underscore-prefixed
   base class removed from package-level `__all__` and import. Still importable
   directly from `cli.base`.

3. **Cover goose.py `_apply_backend_defaults` guard clause** — 6 tests for
   empty commands, single-element, non-goose, non-run subcommands, and
   existing builtin flag.

4. **Cover codex.py Docker env hint** — 3 tests verifying auth failure message
   includes Docker env hint and OPENAI_API_KEY guidance.

5. **Tests** — `test_v213_public_api_cleanup_coverage.py` with 20 new tests.

## Tasks

- [x] Rename `_parse_str_list` → `parse_str_list` in registry.py
- [x] Rename `_parse_positive_int` → `parse_positive_int` in registry.py
- [x] Rename `_parse_optional_str` → `parse_optional_str` in registry.py
- [x] Update all import sites (iterative.py, test files)
- [x] Add to `__all__` in registry.py
- [x] Remove `_TwoPhaseCLIHand` from `cli/__init__.py` `__all__` and import
- [x] Add goose.py `_apply_backend_defaults` guard clause tests
- [x] Add codex.py Docker env hint test
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
- 5209 passed, 216 skipped
