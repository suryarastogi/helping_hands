# v219 — Extract finalization preconditions & status message dispatch tables

**Status:** Completed
**Created:** 2026-03-16

## Motivation

`_finalize_repo_pr()` in `base.py` has a 37-line validation block (lines
1100–1136) that checks 6 preconditions with early returns. Extracting this
into `_validate_finalization_preconditions()` makes the orchestrator cleaner
and the validation independently testable.

`_format_pr_status_message()` and `_format_ci_fix_message()` in `cli/base.py`
use sequential if/elif chains to map status values to message strings. These
are classic dict-dispatch candidates — replacing them with `_PR_STATUS_TEMPLATES`
and `_CI_FIX_TEMPLATES` module-level dicts improves readability and makes the
mapping explicit.

## Tasks

- [x] Create active plan
- [x] Extract `_validate_finalization_preconditions()` from `_finalize_repo_pr()`
- [x] Convert `_format_pr_status_message()` to dict-dispatch
- [x] Convert `_format_ci_fix_message()` to dict-dispatch
- [x] Add unit tests for all changes
- [x] Run ruff + ty + pytest
- [x] Update docs

## Completion criteria

- `_finalize_repo_pr()` reduced by ~30 lines
- Status formatters use dict lookup instead of if/elif chains
- All existing tests pass
- New tests cover extracted methods
- Quality gates green
