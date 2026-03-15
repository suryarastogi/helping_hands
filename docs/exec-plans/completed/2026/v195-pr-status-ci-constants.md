# v195 — Extract PR status / CI conclusion constants, DRY model sentinels, CI poll multiplier

**Status:** completed
**Created:** 2026-03-15
**Branch:** helping-hands/claudecodecli-bfc17b62

## Goal

Replace repeated bare string literals used as a mini-protocol between
`base.py` and `cli/base.py` (PR status values like `"created"`, `"updated"`,
`"missing_token"`, and CI conclusion values like `"pending"`, `"no_checks"`,
`"success"`) with named module-level constants. A typo in these strings would
cause a silent bug. Also extract the CI poll `* 2` magic multiplier and the
`("default", "None")` model sentinel tuple shared across CLI hands.

## Tasks

- [x] Add `_PR_STATUS_*` constants to `base.py` (13 values)
- [x] Add `_CI_CONCLUSION_*` constants to `cli/base.py` (success, pending, no_checks)
- [x] Replace all bare string occurrences in `base.py`, `cli/base.py`, `iterative.py`
- [x] Extract `_CI_POLL_MAX_MULTIPLIER = 2` constant in `cli/base.py`
- [x] Extract `_MODEL_SENTINEL_VALUES` frozenset in `cli/base.py` for shared CLI model resolution
- [x] Use `_MODEL_SENTINEL_VALUES` in `cli/opencode.py` (imports from base)
- [x] Write tests for all new constants (value, type, usage consistency)
- [x] Run quality checks (ruff, ty, pytest)
- [x] Update Week-12 log and PLANS.md

## Completion criteria

- All PR status and CI conclusion bare strings replaced with named constants
- CI poll magic number and model sentinels extracted
- Tests verify constant values and cross-module usage
- All quality gates pass
- Test count increases (4679 → 4721, +42 new)
