# v263: Extract _run_git_diff() helper in pr_description.py

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Goal

Extract a `_run_git_diff()` helper function to deduplicate three nearly identical
`subprocess.run(["git", "diff", ...])` blocks in `pr_description.py`. Each block
repeats the same pattern: subprocess call with `capture_output=True`, `text=True`,
`check=False`, `timeout=_GIT_DIFF_TIMEOUT_S`, plus identical `FileNotFoundError`
and `TimeoutExpired` exception handling.

## Tasks

- [x] Create active plan
- [x] Add `_run_git_diff()` helper to `pr_description.py`
- [x] Refactor `_get_diff()` to use `_run_git_diff()`
- [x] Refactor `_get_uncommitted_diff()` to use `_run_git_diff()`
- [x] Add tests for `_run_git_diff()`
- [x] Run lint, type check, tests
- [x] Update docs, move plan to completed

## Completion criteria

- No duplicate `subprocess.run(["git", "diff", ...])` + exception handling blocks
- `_run_git_diff()` handles FileNotFoundError, TimeoutExpired, non-zero exit
- All 6151 tests pass, 272 skipped, 79% coverage
- 17 new tests cover the extracted helper

## Files touched

- `src/helping_hands/lib/hands/v1/hand/pr_description.py` (add helper, refactor)
- `tests/test_v263_run_git_diff_helper.py` (17 new tests)
- `docs/PLANS.md` (index update)
