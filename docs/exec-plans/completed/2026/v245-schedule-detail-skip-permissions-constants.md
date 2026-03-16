# v245 — Extract _SCHEDULE_NOT_FOUND_DETAIL and _SKIP_PERMISSIONS_FLAG constants

**Status:** Completed
**Date:** 2026-03-16

## Problem

- `"Schedule not found"` was repeated as a bare string literal in 5 HTTPException
  `detail=` arguments across the schedule endpoints in `app.py`.
- `"--dangerously-skip-permissions"` was repeated as a bare string literal in 4
  places across `_apply_backend_defaults()` and `_retry_command_after_failure()`
  in `claude.py`.

## Changes

### `src/helping_hands/server/app.py`
- Extracted `_SCHEDULE_NOT_FOUND_DETAIL = "Schedule not found"` constant
- Replaced 5 bare string literals in `get_schedule`, `delete_schedule`,
  `enable_schedule`, `disable_schedule`, and `trigger_schedule` endpoints

### `src/helping_hands/lib/hands/v1/hand/cli/claude.py`
- Extracted `_SKIP_PERMISSIONS_FLAG = "--dangerously-skip-permissions"` constant
- Added to `__all__` exports
- Replaced 4 bare string literals in `_apply_backend_defaults()` and
  `_retry_command_after_failure()`

### `tests/test_v161_all_exports.py`
- Updated `TestClaudeCodeHandAllExport` to expect 4 exports (was 3)
- Updated expected private names list to include `_SKIP_PERMISSIONS_FLAG`

### `tests/test_v245_schedule_detail_skip_permissions_constants.py` (new)
- 17 passed, 3 skipped (fastapi-dependent runtime tests)
- Constant value, type, and format tests
- AST-based source consistency tests (no bare literals remain)
- Behavioral tests for `_apply_backend_defaults` and `_retry_command_after_failure`

## Test results

- **17 new tests** (3 skipped without fastapi)
- **5810 passed**, 249 skipped, 0 failures
- All lint/format checks pass
