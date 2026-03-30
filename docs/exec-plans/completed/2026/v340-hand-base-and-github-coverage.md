# v340 — Hand Base & GitHub Coverage Hardening

**Status:** Completed
**Created:** 2026-03-30
**Theme:** Close remaining testable coverage gaps in `hand/base.py` and `lib/github.py`

## Goal

Cover the remaining testable branches in core hand and GitHub modules:
- `base.py` 99% → 100% (lines 403-404, 407, 831)
- `github.py` 99% → 99%+ (line 949 — statement now covered)

## Tasks

- [x] Add `_working_tree_is_clean` tests: TimeoutExpired, OSError, dirty tree, clean tree, nonzero rc, whitespace-only stdout
- [x] Add `_push_to_existing_pr` clean-tree test: rev-parse path (base.py:831)
- [x] Add `add_to_project_v2` tests: org project not found, user project not found, missing org key
- [x] Run tests, verify coverage improvement
- [x] Update docs (INTENT.md, exec plan, PLANS.md)

## Completion criteria

- [x] All new tests pass — 6590 passed, 0 failures
- [x] No regressions in existing tests
- [x] Lines 403-404, 407, 831 in base.py covered — base.py now 100%
- [x] Line 949 in github.py covered

## Results

- **10 new tests** in `test_v340_hand_base_github_coverage.py`
- **6590 backend tests passed**, 75.93% overall coverage (up from 75.84%)
- `base.py`: 99% (4 missed lines) → 100% (0 missed lines)
- `github.py`: 99% (1 missed statement) → 99% (0 missed statements, 1 partial branch)
- 43 files at complete coverage (up from 42)
