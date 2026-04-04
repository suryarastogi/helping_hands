# v347 — Validation Coverage & Week-14 Consolidation

**Date:** 2026-04-04
**Status:** Completed

## Goal

Close the two untested functions in `validation.py` (`has_cli_flag` and
`install_hint`) and consolidate the Week-14 daily summaries.

## Tasks

1. **Add `has_cli_flag` tests** — bare flag, flag=value, missing flag, empty
   list, partial matches, multiple flags — **Done** (10 tests)
2. **Add `install_hint` tests** — normal extras, output format verification —
   **Done** (4 tests)
3. **Run tests** — verify all pass, check coverage delta — **Done** (135 passed)
4. **Week-14 consolidation** — consolidate 2026-03-30 daily into Week-14 weekly
   summary (Mar 30 – Apr 5, 2026) — **Done**
5. **Update docs** — INTENT.md, PLANS.md — **Done**

## Changes

- `tests/test_validation.py` — Added `TestHasCliFlag` (10 tests) and
  `TestInstallHint` (4 tests) classes
- `docs/exec-plans/completed/2026/Week-14.md` — New weekly consolidation
- `INTENT.md` — Added completion entry
- `docs/PLANS.md` — Added v347 to completed plans index

## Acceptance criteria

- [x] `has_cli_flag` and `install_hint` have dedicated test classes
- [x] All existing tests still pass (135 passed in test_validation + test_config)
- [x] Week-14 weekly consolidation created
- [x] Plan moved to completed
