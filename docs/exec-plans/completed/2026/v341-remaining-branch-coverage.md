# v341 — Remaining Branch Coverage Gaps

**Status:** Completed
**Created:** 2026-03-30
**Completed:** 2026-03-30
**Theme:** Close last testable branch partials in non-server modules

## Goal

Cover the remaining branch partial lines in `cli/base.py`, `github.py`, and
`e2e.py` that are not already tracked as untestable in the tech debt tracker.

## Tasks

- [x] `github.py:820→822` — `_graphql()` without-variables branch (payload omits `variables` key)
- [x] `e2e.py:224→239` — `dry_run=True` with `pr_number` set (skips head branch checkout)
- [x] `cli/base.py:1535` — `_poll_ci_checks` deadline exceeded before sleep (`wait <= 0` break)
- [x] `cli/base.py:1719-1727` — `_ci_fix_loop` loop-level timeout (`time.monotonic() > loop_deadline`)
- [x] Run tests, verify improvements
- [x] Update docs

## Completion criteria

All four branch partials covered by new tests. Full test suite passes (existing
tests unbroken). Coverage increases. Docs updated.

## Results

- **5 new tests** in `tests/test_v341_remaining_branch_coverage.py`
- `github.py`: 99% → 100% (branch `820→822` covered)
- `e2e.py`: 99% → 100% (branch `224→239` covered)
- `cli/base.py`: 99% (4 miss, 3 partials) → 99% (0 miss, 1 partial — only `1272→1281` heartbeat remains, tracked in tech debt)
- **6595 tests passed**, 0 failures, 76.02% coverage (up from 75.93%)
- 45 files at 100% coverage (up from 43)
