# v223 — Input validation: PR metadata, finalize entry, CLI command

**Date:** 2026-03-16
**Status:** Completed

## Goal

Three self-contained input validation improvements following the established `require_non_empty_string` pattern:

1. Validate `pr_url`, `pr_number`, `pr_branch`, `pr_commit` in `_pr_result_metadata()` (base.py)
2. Validate `backend`, `prompt` in `_finalize_repo_pr()` (base.py)
3. Validate `cmd` list in `_invoke_cli_with_cmd()` (cli/base.py) — reject empty command lists, add docstring

## Tasks

- [x] Add `require_non_empty_string` validation to `_pr_result_metadata` for all 4 string fields
- [x] Add `require_non_empty_string` validation to `_finalize_repo_pr` entry for `backend`, `prompt`
- [x] Add empty-list validation and docstring to `_invoke_cli_with_cmd` for `cmd` parameter
- [x] Write tests for all new validation paths
- [x] Run ruff + ty + pytest

## Changes

### `src/helping_hands/lib/hands/v1/hand/base.py`

- **`_pr_result_metadata()`**: Added `require_non_empty_string` validation for `pr_url`, `pr_number`, `pr_branch`, `pr_commit` at entry. Prevents silent population of metadata with empty/whitespace values.
- **`_finalize_repo_pr()`**: Added `require_non_empty_string` validation for `backend` and `prompt` at entry. Summary intentionally excluded — AI backends may produce empty output, and `_build_generic_pr_body` already handles the empty-summary case with a fallback.

### `src/helping_hands/lib/hands/v1/hand/cli/base.py`

- **`_invoke_cli_with_cmd()`**: Added Google-style docstring with Args/Returns/Raises. Added precondition validation rejecting empty command lists and empty first elements before subprocess creation.

### Tests

- **`tests/test_v223_input_validation_pr_metadata_finalize_cli_cmd.py`**: 20 tests across 5 classes:
  - `TestPrResultMetadataValidation` (9): empty/whitespace rejection for 4 fields, valid passthrough
  - `TestFinalizePrValidation` (4): empty/whitespace rejection for backend, prompt
  - `TestInvokeCliWithCmdValidation` (3): empty list, empty first element, None first element
  - `TestSourceConsistency` (4): validation calls exist in source, docstring present
- **`tests/test_v208_pr_status_enum.py`**: Updated `test_returns_same_dict_object` to use non-empty values (was passing empty strings)

## Completion criteria

- `_pr_result_metadata` rejects empty/whitespace `pr_url`, `pr_number`, `pr_branch`, `pr_commit`
- `_finalize_repo_pr` rejects empty/whitespace `backend`, `prompt`
- `_invoke_cli_with_cmd` rejects empty command list
- All existing tests pass, new tests cover all changes

## Results

- **20 new tests, 1 existing test updated**
- **5377 passed, 219 skipped**, coverage 78.76%
