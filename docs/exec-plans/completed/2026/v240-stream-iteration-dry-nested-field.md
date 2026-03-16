# v240 — DRY stream iteration processing, _extract_nested_str_field

**Status:** completed
**Created:** 2026-03-16
**Completed:** 2026-03-16

## Motivation

`BasicLangGraphHand.stream()` and `BasicAtomicHand.stream()` share an identical
18-line post-response processing block (apply edits, collect feedback, merge
summary, check satisfaction, finalize PR) and a 9-line post-loop max-iterations
finalization block. Extracting these into shared methods on `_BasicIterativeHand`
eliminates the duplication.

Similarly, `_extract_task_id()` and `_extract_task_name()` in `server/app.py`
share identical structure (key lookup + recursive request fallback), differing
only by key names. Extracting the common logic into `_extract_nested_str_field()`
makes both functions trivial one-liners.

## Changes

### Code changes

- **Added `_process_stream_iteration(content, prompt)` → `(messages, prior, satisfied)`**
  to `_BasicIterativeHand` — encapsulates inline edits, tool feedback, summary
  merge, satisfaction check, and PR finalization for stream iterations
- **Added `_stream_max_iterations_tail(prompt, prior)` → `list[str]`** to
  `_BasicIterativeHand` — encapsulates post-loop PR finalization + max-iterations
  message
- **Replaced 2× inline 18-line stream iteration blocks** in
  `BasicLangGraphHand.stream()` and `BasicAtomicHand.stream()` with
  `_process_stream_iteration()` calls (4 lines each)
- **Replaced 2× inline 9-line post-loop blocks** with
  `_stream_max_iterations_tail()` calls (2 lines each)
- **Added `_extract_nested_str_field(entry, keys)`** to `server/app.py` —
  generic key lookup + recursive request fallback
- **Simplified `_extract_task_id()` and `_extract_task_name()`** to one-liner
  delegates to `_extract_nested_str_field()`
- **Updated 2 AST source consistency tests** in `test_v220_pr_status_line_cli_validation.py`
  to check for `_process_stream_iteration` instead of inline `_pr_status_line`

### Tasks completed

- [x] Extract `_process_stream_iteration` in `_BasicIterativeHand`
- [x] Extract `_stream_max_iterations_tail` in `_BasicIterativeHand`
- [x] Replace 2× inline stream iteration blocks
- [x] Replace 2× inline post-loop blocks
- [x] Extract `_extract_nested_str_field` in `server/app.py`
- [x] Simplify `_extract_task_id` / `_extract_task_name` to delegates
- [x] Update AST source consistency tests
- [x] Tests for `_process_stream_iteration` (11 tests)
- [x] Tests for `_stream_max_iterations_tail` (5 tests)
- [x] Tests for `_extract_nested_str_field` (14 tests, skipped without fastapi)
- [x] Docstring presence tests (2 tests)
- [x] Update PLANS.md

## Test results

- 32 new tests added (18 passed, 14 skipped without fastapi)
- 5738 passed, 239 skipped
- All lint/format checks pass

## Completion criteria

- [x] All tasks checked
- [x] `uv run pytest` passes with no new failures
- [x] `uv run ruff check .` passes
- [x] `uv run ruff format --check .` passes
