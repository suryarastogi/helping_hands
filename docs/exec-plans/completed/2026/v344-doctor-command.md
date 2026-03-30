# v344 — Doctor Command

**Status:** Completed
**Created:** 2026-03-30
**Date:** 2026-03-30
**Theme:** New user onboarding — `helping-hands doctor` environment checker

## Goals

1. **Implement `helping-hands doctor`** — a CLI subcommand that verifies
   environment prerequisites: Python version, git, uv, AI provider keys,
   GitHub token, optional CLI tools, and optional Python extras.
2. **Add comprehensive tests** — 100% statement+branch coverage on the
   new `cli/doctor.py` module, plus integration tests for the `main()`
   dispatcher routing.
3. **Update product spec** — mark the `doctor` requirement as implemented.

## Non-goals

- Interactive first-run banner (separate product spec item)
- `examples/` directory (separate product spec item)
- Quick-start README section (separate product spec item)

## Tasks

- [x] Create `src/helping_hands/cli/doctor.py` with individual check functions
- [x] Add `doctor` subcommand dispatch in `main()` (early intercept before argparse)
- [x] Add `doctor` to `__all__` export in `cli/main.py`
- [x] Write 28 tests covering all check functions, formatting, exit codes, and dispatch
- [x] Fix `test_all_count` assertion (2 → 3) in `test_v161_all_exports.py`
- [x] Verify 100% coverage on `doctor.py`, 76.40% overall
- [x] Update product spec, INTENT.md, PLANS.md, daily consolidation

## Completion criteria

- `helping-hands doctor` runs and reports environment status
- `doctor.py` at 100% statement+branch coverage
- All 6627 tests pass
- Product spec updated with implementation status
