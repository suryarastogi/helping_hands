# v220 — DRY PR status line helper & CLI validation cleanup

**Status:** Completed
**Created:** 2026-03-16

## Motivation

The 4-line PR metadata yield block appears 4 times in `iterative.py`.
Extracting a `_pr_status_line()` static method on `_BasicIterativeHand`
eliminates this duplication and makes the streaming finalization output
consistent. The helper also adds a truthy guard on `_META_PR_STATUS` so
that `None` status (empty metadata) returns empty string instead of
`"\nPR status: None\n"`.

Separately, `cli/main.py` manually validated `--pr-number` and
`--max-iterations` with inline if/print/exit blocks when
`require_positive_int()` from `validation.py` already exists for this purpose.

## Tasks

- [x] Create active plan
- [x] Extract `_pr_status_line(pr_metadata)` → `str` static method on `_BasicIterativeHand`
- [x] Replace 4 blocks in `iterative.py` with the helper
- [x] Use `require_positive_int()` in `cli/main.py` for `--pr-number` and `--max-iterations`
- [x] Add unit tests for all changes
- [x] Run ruff + ty + pytest
- [x] Update docs

## Completion criteria

- 4 PR-status yield blocks in `iterative.py` replaced by `_pr_status_line()` calls
- CLI validation uses shared `require_positive_int()` utility (import added)
- All existing tests pass (v141 tests updated for new error message format)
- 18 new tests cover the helper and CLI validation changes
- Quality gates green (5294 passed, 219 skipped)
