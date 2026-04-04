# v358 — E2E Coverage & Exports Cleanup

**Created:** 2026-04-04
**Status:** Completed

## Goal

Close test gaps in `e2e.py` (`_draft_pr_enabled`, `stream`) and add missing
`__all__` to `multiplayer_yjs.py`. Move completed v357 plans, fix doc structure
tests, update Week-14 summary.

## Tasks

- [x] Move completed v357 plans to `completed/2026/`, mark status Completed
- [x] Update INTENT.md, PLANS.md with v357 completion and v358 active plan
- [x] Add `__all__` to `server/multiplayer_yjs.py`
- [x] Add tests for `E2EHand._draft_pr_enabled` (default true, explicit false,
      explicit true, non-truthy value, yes, whitespace, empty, zero)
- [x] Add tests for `E2EHand.stream()` (delegates to `run()`, yields message,
      exactly one message)
- [x] Update Week-14 summary with v358 entry
- [x] Run pytest, ruff check, ruff format — all clean
      (6821 passed, 267 skipped, 76.03% coverage)

## Completion criteria

- `_draft_pr_enabled` 100% branch coverage ✓
- `multiplayer_yjs.py` has `__all__` ✓
- All existing tests still pass ✓ (6821 passed)
- ruff check + format clean ✓
