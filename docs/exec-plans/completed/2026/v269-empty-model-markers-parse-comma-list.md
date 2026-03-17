# v269 — Extract _EMPTY_MODEL_MARKERS constant + parse_comma_list helper

**Created:** 2026-03-17
**Status:** Completed
**Tests:** 17 new (6254 passed, 272 skipped)
**Theme:** DRY constant extraction + shared parsing helper

## Motivation

Two small but clear duplication patterns remain after the v247–v268 DRY campaign:

1. `("default", "None")` tuple duplicated in `cli/base.py:363` and `cli/opencode.py:30`
   for detecting placeholder model values.
2. `r.strip() for r in s.split(",") if r.strip()` pattern duplicated in `config.py:169`
   and `app.py:3620` for parsing comma-separated reference repo strings.

## Tasks

- [x] Extract `("default", "None")` as `_EMPTY_MODEL_MARKERS` module-level constant in `cli/base.py`
- [x] Import and use `_EMPTY_MODEL_MARKERS` in `opencode.py`
- [x] Add `parse_comma_list(value: str) -> tuple[str, ...]` to `lib/validation.py`
- [x] Replace inline comma-split patterns in `config.py` and `app.py`
- [x] Add unit tests for `_EMPTY_MODEL_MARKERS` constant
- [x] Add unit tests for `parse_comma_list()` (13 cases)
- [x] Verify `ruff check .` clean
- [x] Verify `ty check` clean
- [x] Verify all tests pass

## Completion criteria

- [x] `_EMPTY_MODEL_MARKERS` defined once, used in both `base.py` and `opencode.py`
- [x] `parse_comma_list()` defined in `validation.py`, used in `config.py` and `app.py`
- [x] New unit tests for both changes
- [x] `ruff check .` clean
- [x] `ty check` clean
- [x] All tests pass
