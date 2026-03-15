# v211 — DRY encoding fallback chain, git ref prefix, check-run status constant

**Status:** Completed
**Created:** 2026-03-15

## Summary

Three self-contained constant extractions: encoding fallback chain in `web.py`,
git ref prefix in `github.py`, and check-run status string in `github.py`.

1. **`_ENCODING_FALLBACK_CHAIN` constant** in `web.py` — Extract the inline
   `("utf-8", "utf-16", "latin-1")` tuple from `_decode_bytes()` to a
   module-level constant with docstring.

2. **`_GIT_REF_PREFIX` constant** in `github.py` — Extract the inline
   `"refs/heads/"` string from `fetch_branch()` to a module-level constant
   with docstring.

3. **`_CHECK_RUN_STATUS_COMPLETED` constant** in `github.py` — Extract the
   inline `"completed"` string used in `get_check_runs()` to a module-level
   constant with docstring, matching the pattern of `_CI_RUN_FAILURE_CONCLUSIONS`.

4. **`tests/test_v211_dry_encoding_ref_prefix_check_status.py`** — 21 versioned
   tests verifying constant values, module-level availability, and usage in
   their respective functions.

## Tasks

- [x] Extract `_ENCODING_FALLBACK_CHAIN` constant in `web.py`
- [x] Extract `_GIT_REF_PREFIX` constant in `github.py`
- [x] Extract `_CHECK_RUN_STATUS_COMPLETED` constant in `github.py`
- [x] Add `tests/test_v211_dry_encoding_ref_prefix_check_status.py` with 21 tests
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
- 5164 passed, 216 skipped
