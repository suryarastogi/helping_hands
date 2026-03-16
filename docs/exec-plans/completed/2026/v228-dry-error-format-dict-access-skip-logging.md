# v228 — DRY error formatting, consistent dict access, skip logging

**Status:** Completed
**Created:** 2026-03-16
**Branch:** helping-hands/claudecodecli-153b72b7

## Problem

1. **Duplicated error formatting** — `_execute_read_requests` (lines 355-368)
   and `_execute_tool_requests` (lines 627-636) in `iterative.py` both format
   errors as `@@*_RESULT: {name}\nERROR: {msg}` with nearly identical patterns.
   A shared `_format_error_result()` static method would DRY this.

2. **Inconsistent dict access** — `_pr_status_line` (line 534-535) uses
   `.get(_META_PR_URL)` to check existence, then immediately accesses
   `pr_metadata[_META_PR_URL]` with bracket notation. Should use the `.get()`
   return value directly to be consistent and avoid a redundant lookup.

3. **Silent path skipping** — `_build_tree_snapshot` (lines 708-711) silently
   `continue`s when `normalize_relative_path` raises ValueError, with no debug
   logging. This makes it hard to diagnose missing files in tree snapshots.

## Tasks

- [x] Extract `_format_error_result(tag, name, message)` static method
- [x] Replace error formatting in `_execute_read_requests` (4 except blocks)
- [x] Replace error formatting in `_execute_tool_requests` (2 error sites)
- [x] Fix `_pr_status_line` to use `.get()` value directly
- [x] Add `logger.debug()` for skipped paths in `_build_tree_snapshot`
- [x] Add tests for `_format_error_result()`
- [x] Add tests for `_pr_status_line` dict access consistency
- [x] Add test for skipped path logging
- [x] Run full test suite, lint, type check

## Completion criteria

- Error formatting uses shared helper in both execution methods
- Dict access is consistent (no mixed `.get()` / `[]` for same key)
- Skipped paths are logged at DEBUG level
- Tests pass, lint clean, types clean
