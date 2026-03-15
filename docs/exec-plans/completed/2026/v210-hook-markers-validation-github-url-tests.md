# v210 — Hook failure markers constant, validation + github_url test coverage

**Status:** Completed
**Created:** 2026-03-15

## Summary

Three self-contained improvements: extract inline hook-failure markers tuple to a
module-level constant, add dedicated unit tests for the `validation` module, and
add dedicated unit tests for the `github_url` module.

1. **`_GIT_HOOK_FAILURE_MARKERS` constant** in `base.py` — Extract the inline
   `markers` tuple from `_is_git_hook_failure()` to a module-level constant with
   docstring, matching the project pattern of pre-extracted marker tuples.

2. **`tests/test_validation.py`** — 21 dedicated unit tests for
   `require_non_empty_string` and `require_positive_int` covering all branches:
   valid returns, empty/whitespace rejection, error message formatting, unicode,
   multiline, zero/negative rejection.

3. **`tests/test_github_url.py`** — 33 dedicated unit tests for all 4 public
   functions plus constants: `validate_repo_spec` (valid formats, rejection cases),
   `build_clone_url` (no token, explicit token, env vars, overrides, whitespace),
   `redact_credentials` (single/multiple URLs, preserving text), `noninteractive_env`
   (env vars set, copy semantics).

4. **`tests/test_v210_hook_markers_validation_github_url.py`** — 16 versioned
   tests verifying the constant extraction, module contracts, and API surfaces.

## Tasks

- [x] Extract `_GIT_HOOK_FAILURE_MARKERS` constant in `base.py`
- [x] Add `tests/test_validation.py` with 21 tests
- [x] Add `tests/test_github_url.py` with 33 tests
- [x] Add `tests/test_v210_hook_markers_validation_github_url.py` with 16 tests
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
- 5143 passed, 216 skipped
