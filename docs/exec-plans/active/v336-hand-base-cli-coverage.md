# v336 — Hand Base & CLI Hand Coverage Hardening

**Status:** completed
**Created:** 2026-03-29

## Goal

Close remaining coverage gaps in `Hand` base class (99% → 100%) and
`_TwoPhaseCLIHand` (99% → ~100%). Target lines: `base.py` 403-404, 407, 831;
`cli/base.py` 1535, 1719-1727. Consolidate Mar 29 daily plans.

## Tasks

- [x] Move v335 to completed, create 2026-03-29.md daily consolidation
- [x] Add tests for `_working_tree_is_clean` TimeoutExpired/OSError exception paths (lines 403-404)
- [x] Add test for `_working_tree_is_clean` clean/dirty tree return paths (line 407)
- [x] Add test for `_push_to_existing_pr` clean working tree branch (line 831)
- [x] Add test for `_ci_fix_loop` loop_deadline timeout (lines 1719-1727)
- [x] Add test for `_poll_ci_checks` poll wait ≤ 0 break (line 1535)
- [x] Run full test suite, verify ≥75% coverage gate
- [x] Update INTENT.md, PLANS.md

## Results

- 4 new `_working_tree_is_clean` tests: TimeoutExpired, OSError, clean tree (True),
  dirty tree (False)
- 1 new `_push_to_existing_pr` test: clean working tree skips commit, uses HEAD SHA
- 1 new `_ci_fix_loop` test: loop_deadline exceeded returns EXHAUSTED with message
- 1 new `_poll_ci_checks` test: poll breaks when remaining wait ≤ 0
- Hand base.py coverage: 99% → 100% (fully covered) ✓
- cli/base.py coverage: 99% (4 miss) → 99% (1 miss, branch-only) ✓
- 6526 backend tests passed, 0 failures, 75.95% coverage ✓
- Docs updated ✓

## Completion criteria

- Hand base.py coverage: 99% → 100% ✓
- cli/base.py coverage: 99% → ~100% ✓ (1 branch remaining: line 1272→1281)
- All existing tests still pass ✓ (6526 passed)
- Docs updated ✓
