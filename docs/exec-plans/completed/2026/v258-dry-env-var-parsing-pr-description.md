# v258 — DRY env var parsing in pr_description.py

**Status:** Completed
**Created:** 2026-03-17

## Problem

`_timeout_seconds()` and `_diff_char_limit()` in `pr_description.py` share an
identical pattern:

1. `os.environ.get(env_var_name)`
2. Return default if `None`
3. Parse (`float(raw.strip())` or `int(raw.strip())`)
4. Warn "ignoring non-numeric …" on `ValueError`, return default
5. Warn "ignoring non-positive …" if `<= 0`, return default
6. Return parsed value

This results in 4 nearly identical `logger.warning()` calls (2 per function)
and duplicated control flow.

## Tasks

- [x] Extract `_parse_positive_env_var(name, default, type_fn)` helper
- [x] Refactor `_timeout_seconds()` to delegate to helper
- [x] Refactor `_diff_char_limit()` to delegate to helper
- [x] Write tests covering the helper and refactored functions
- [x] Run full test suite — 6023 passed, 270 skipped, 78.91% coverage

## Completion criteria

- `_timeout_seconds()` and `_diff_char_limit()` are 1–2 line delegations
- Helper handles non-numeric, non-positive, and `None` cases with warnings
- All existing `test_pr_description.py` tests continue to pass
- New tests cover helper directly

## Files modified

- `src/helping_hands/lib/hands/v1/hand/pr_description.py`
- `tests/test_v258_dry_env_var_parsing_pr_description.py`
