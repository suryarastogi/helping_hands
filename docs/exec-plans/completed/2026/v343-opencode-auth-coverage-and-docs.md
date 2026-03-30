# v343 — OpenCode Auth Coverage, Lint Fix & Design Doc

**Status:** Completed
**Created:** 2026-03-30

## Scope

Close remaining coverage gap in `OpenCodeCLIHand._describe_auth()` (68% → 100%),
fix ruff E402 lint violation in `test_v342`, add GitHub Issue Integration design
doc (v325-v329 features), and update daily consolidation.

## Tasks

- [x] Fix ruff E402 lint error in `test_v342_server_helper_coverage.py`
- [x] Update 2026-03-30 daily consolidation to include v342
- [x] Add GitHub Issue Integration design doc (`docs/design-docs/github-issue-integration.md`)
- [x] Update design-docs index with new doc
- [x] Add `_describe_auth` tests for `OpenCodeCLIHand` (6 tests: no model,
      model without slash, known provider key set, known provider key not set,
      unknown provider, default marker)
- [x] Add class-attribute tests for `OpenCodeCLIHand` constants (5 tests)
- [x] Run full test suite, verify coverage improvement
- [x] Update INTENT.md and PLANS.md

## Completion criteria

All tests pass, `opencode.py` at 100% coverage, lint clean, docs updated.

## Results

11 new tests added to `test_cli_hand_opencode.py` (6 `_describe_auth` + 5 class
attributes). `opencode.py` coverage 68% → 100%. Fixed ruff E402/I001 lint error
in `test_v342_server_helper_coverage.py`. Added `docs/design-docs/github-issue-integration.md`
covering v325-v329 features. Updated 2026-03-30 daily consolidation to include v342.
All 6606 tests pass, 76.02% coverage.
