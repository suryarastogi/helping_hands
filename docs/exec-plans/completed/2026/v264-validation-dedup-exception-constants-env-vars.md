# v264: Shared validation, exception tuple constants, env var constants

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Goal

Three self-contained DRY improvements:

1. **Shared owner/repo validation** — `github.py:_validate_full_name()` duplicates
   the split/check logic in `github_url.py:validate_repo_spec()`. Refactor
   `_validate_full_name` to delegate to `validate_repo_spec` (adding the extra
   whitespace check).

2. **Exception tuple constants** — Extract repeated exception tuples:
   - `_TOOL_EXECUTION_ERRORS` in `iterative.py` (7-type tuple)
   - `_RUN_ASYNC_ERRORS` shared between `iterative.py` and `atomic.py`
     (identical 5-type tuple, catch-and-reraise pattern)

3. **Env var name constants in config.py** — Extract 9 bare `"HELPING_HANDS_*"`
   strings as module-level `_ENV_*` constants, matching the pattern in
   `github_url.py` and `pr_description.py`.

## Tasks

- [x] Create active plan
- [x] Refactor `_validate_full_name` to use `validate_repo_spec`
- [x] Extract `_TOOL_EXECUTION_ERRORS` constant in `iterative.py`
- [x] Extract `_RUN_ASYNC_ERRORS` constant shared by `iterative.py` and `atomic.py`
- [x] Extract env var constants in `config.py`
- [x] Add tests for all changes
- [x] Run lint, type check, tests
- [x] Update docs, move plan to completed

## Completion criteria

- No duplicate owner/repo validation logic
- Exception tuples are named constants, not inline
- All env var names in config.py are constants
- All 6184 tests pass, 272 skipped, 79% coverage
- 33 new tests cover all changes

## Files touched

- `src/helping_hands/lib/github.py` (delegate to `validate_repo_spec`)
- `src/helping_hands/lib/hands/v1/hand/iterative.py` (add constants, use them)
- `src/helping_hands/lib/hands/v1/hand/atomic.py` (import `_RUN_ASYNC_ERRORS`)
- `src/helping_hands/lib/config.py` (add `_ENV_*` constants)
- `tests/test_v264_validation_dedup_exception_constants.py` (33 new tests)
- `tests/test_v248_git_not_found_constants_narrow_exceptions.py` (update source checks)
- `docs/PLANS.md` (index update)
