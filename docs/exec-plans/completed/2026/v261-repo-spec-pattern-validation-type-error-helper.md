# v261: Extract REPO_SPEC_PATTERN, invalid_repo_msg, format_type_error

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Goal

Three self-contained DRY improvements:

1. **Extract `REPO_SPEC_PATTERN`** — identical regex `r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"` was
   duplicated in `cli/main.py`, `server/celery_app.py`, and `lib/hands/v1/hand/base.py`.
   Moved to `github_url.py` as a public constant and imported from all call sites.

2. **Extract `invalid_repo_msg()`** — identical error message
   `f"{repo} is not a directory or owner/repo reference"` in `cli/main.py` and
   `server/celery_app.py`. Added shared formatter to `github_url.py`.

3. **Extract `format_type_error()`** in `validation.py` — three near-identical
   `f"{name} must be a {type}, got {type(value).__name__}"` messages replaced with
   a shared helper.

## Tasks

- [x] Create active plan
- [x] Add `REPO_SPEC_PATTERN` to `github_url.py`
- [x] Add `invalid_repo_msg()` to `github_url.py`
- [x] Replace inline pattern in `cli/main.py`
- [x] Replace inline pattern in `server/celery_app.py`
- [x] Replace inline pattern in `lib/hands/v1/hand/base.py`
- [x] Replace error message in `cli/main.py`
- [x] Replace error message in `server/celery_app.py`
- [x] Add `format_type_error()` to `validation.py` and use in 3 places
- [x] Add tests (29 new)
- [x] Run lint, type check, tests
- [x] Update docs

## Completion criteria

- No bare `r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"` remains outside `github_url.py`
- No duplicate "is not a directory or owner/repo reference" messages
- No duplicate type-error format strings in `validation.py`
- All 6110 tests pass, 272 skipped, 79% coverage
- 29 new tests cover the shared constants/helpers

## Files touched

- `src/helping_hands/lib/github_url.py` (add `REPO_SPEC_PATTERN` + `invalid_repo_msg()`)
- `src/helping_hands/lib/validation.py` (add `format_type_error()`)
- `src/helping_hands/cli/main.py` (import constant + helper, remove local `_REPO_SPEC_PATTERN`)
- `src/helping_hands/server/celery_app.py` (import constant + helper)
- `src/helping_hands/lib/hands/v1/hand/base.py` (import `REPO_SPEC_PATTERN`)
- `tests/test_v261_repo_spec_pattern_validation_type_error.py` (29 new tests)
- `tests/test_github_url.py` (update `__all__` expectation)
- `tests/test_validation.py` (update `__all__` expectation)
- `tests/test_v179_dry_github_url_server_constants.py` (update `__all__` expectation)
- `tests/test_v210_hook_markers_validation_github_url.py` (update `__all__` expectations)
