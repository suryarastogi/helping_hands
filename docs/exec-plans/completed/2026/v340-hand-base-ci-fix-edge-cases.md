# v340 — Hand Base & CI Fix Edge Case Coverage

**Status:** Completed
**Created:** 2026-03-30
**Theme:** Close testable coverage gaps in Hand base class and CLI hand CI fix loop

## Goal

Cover remaining testable branches in `hand/base.py` (99% → 99%+) and
`hand/cli/base.py` (99% → 99%+):

- `_working_tree_is_clean` has zero direct unit tests (only ever mocked)
- CI fix loop timeout path (lines 1718-1727) never exercised
- CI poll `wait <= 0` break path (line 1535) never exercised

## Tasks

- [x] Add `_working_tree_is_clean` unit tests: TimeoutExpired, OSError, clean tree, dirty tree, non-zero returncode
- [x] Add `_poll_ci_checks` deadline-reached break test (wait ≤ 0)
- [x] Add `_ci_fix_loop` loop timeout test
- [x] Run tests, verify coverage improvement
- [x] Update docs (INTENT.md, daily consolidation)

## Completion criteria

- [x] All new tests pass — 6587 passed, 0 failures
- [x] No regressions in existing tests
- [x] `_working_tree_is_clean` all branches covered (only line 831 remains — different method)
- [x] CI fix timeout path exercised
- [x] CI poll deadline break path exercised

## Results

- **7 new tests** in `test_v340_hand_base_ci_fix_edge_cases.py`
  - 5 `_working_tree_is_clean` tests: TimeoutExpired, OSError, non-zero returncode, dirty tree, clean tree
  - 1 `_poll_ci_checks` test: wait ≤ 0 deadline break
  - 1 `_ci_fix_loop` test: monotonic loop timeout → EXHAUSTED
- **base.py** lines 403-404, 407 now covered (was 4 missed → 1 missed)
- **cli/base.py** lines 1535, 1719-1727 now covered (was 4 missed → 0 missed)
- 6587 backend tests passed, 75.95% coverage (up from 75.84%)
