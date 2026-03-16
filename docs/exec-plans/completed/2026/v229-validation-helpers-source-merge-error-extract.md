# v229 — Validation helpers, source-tag merge, error extraction

**Created:** 2026-03-16
**Status:** Completed

## Goal

Three self-contained improvements to reduce inline boilerplate and improve
testability:

1. **`require_positive_float`** in `validation.py` — mirrors `require_positive_int`
   for float validation (timeout configs, numeric bounds).
2. **`_first_validation_error_msg()`** in `app.py` — extract the Pydantic
   `ValidationError` → user-friendly string logic into a named, testable helper.
3. **`_merge_source_tags()`** in `app.py` — extract the `source` string-set
   parsing (`"a+b".split("+")` / `"+".join(sorted(...))`) into a helper.

## Tasks

- [x] Add `require_positive_float` to `validation.py` + update `__all__`
- [x] Add tests for `require_positive_float` in `test_validation.py`
- [x] Extract `_first_validation_error_msg()` in `app.py`
- [x] Extract `_merge_source_tags()` in `app.py`
- [x] Add tests for both new app.py helpers
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All new helpers have full branch coverage tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/lib/validation.py`
- `src/helping_hands/server/app.py`
- `tests/test_validation.py`
- `tests/test_server_app_helpers.py`
