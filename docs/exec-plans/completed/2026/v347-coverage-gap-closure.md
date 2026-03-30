# v347 — Coverage Gap Closure

**Status:** Completed
**Created:** 2026-03-30

## Goal

Close the remaining non-server coverage gaps to push overall coverage above
the 75% threshold. Coverage was at 74.99% with gaps in:

- `cli/base.py` `_LinePrefixEmitter` (lines 312-320, 325-329)
- `cli/devin.py` `_pr_description_cmd` / `_pr_description_prompt_as_arg` (lines 38-40, 44)
- `cli/opencode.py` `_pr_description_cmd` (lines 35-37)
- `github.py` `update_pr` (lines 542-549)

## Tasks

- [x] Add `_LinePrefixEmitter.__call__` and `flush` unit tests (11 tests)
- [x] Add `DevinCLIHand._pr_description_cmd` and `_pr_description_prompt_as_arg` tests (3 tests)
- [x] Add `OpenCodeCLIHand._pr_description_cmd` tests (2 tests)
- [x] Add `update_pr` tests for `github.py` (5 tests)
- [x] Verify tests pass and coverage ≥ 75%

## Completion criteria

- All 21 new tests pass
- Overall coverage ≥ 75.0%
- `cli/base.py` lines 312-320, 325-329 covered
- `cli/devin.py` lines 38-40, 44 covered
- `cli/opencode.py` lines 35-37 covered
- `github.py` lines 542-549 covered

## Result

21 new tests. 6670 tests passed, 75.44% coverage (up from 74.99%).

- `cli/base.py`: 98% → 99% (0 statement miss, 1 branch partial remaining)
- `github.py`: 98% → 100%
- `cli/devin.py`: 92% → covered
- `cli/opencode.py`: 90% → covered
