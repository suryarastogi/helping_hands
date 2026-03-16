# v216 — Metadata Key Constants

**Status:** Completed
**Completed:** 2026-03-16
**Created:** 2026-03-16
**Goal:** Extract hardcoded metadata dictionary key strings (`"pr_status"`,
`"pr_commit"`, `"pr_branch"`, `"pr_url"`, `"pr_number"`, `"ci_fix_status"`,
`"ci_fix_attempts"`, `"ci_fix_error"`) to module-level constants, reducing 72
scattered string literals across 9 files to a single source of truth.

## Context

The PR finalization and CI-fix workflows communicate via a `dict[str, str]`
metadata payload. The key names are repeated as bare strings 72 times across
`base.py`, `cli/base.py`, `iterative.py`, `e2e.py`, `langgraph.py`,
`atomic.py`, `app.py`, `celery_app.py`, and `schedules.py`. A typo in any
one of them would silently break the protocol. Extracting to constants
eliminates that risk.

## Tasks

- [x] Add `_META_*` constants to `base.py` (PR keys) and `cli/base.py` (CI keys)
- [x] Replace all 20 occurrences in `base.py`
- [x] Replace all 27 occurrences in `cli/base.py`
- [x] Replace occurrences in `iterative.py`, `e2e.py`, `langgraph.py`, `atomic.py`
- [x] Verify `app.py`, `celery_app.py`, `schedules.py` — uses are form/query/dataclass fields, not metadata protocol (no change needed)
- [x] Add tests for constant values and usage consistency
- [x] Run lint, type check, and tests — verify green
- [x] Update PLANS.md and move plan to completed

## Completion criteria

- All bare metadata key strings replaced with constants
- All tests pass, no lint/format/type regressions
- Coverage unchanged or improved
