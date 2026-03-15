# v204 — DRY form defaults, truthy values, inline import, tool dispatch table

**Status:** Completed
**Created:** 2026-03-15

## Problem

1. `enqueue_build_form` defaults `backend` to hardcoded `"codexcli"` instead of
   `_DEFAULT_BACKEND` (`"claudecodecli"`), causing form submissions to use the
   wrong backend. Also `max_iterations` and `ci_check_wait_minutes` use hardcoded
   literals instead of the shared constants.

2. `_is_running_in_docker()` uses inline `{"1", "true", "yes"}` instead of the
   canonical `_TRUTHY_VALUES` from `config.py`.

3. `_fetch_claude_usage` imports `time` inside the function body unnecessarily.

4. `_StreamJsonEmitter._summarize_tool()` is a 55-line if/elif chain where ~7
   cases follow the identical `"ToolName {input_data[key]}"` pattern.

## Tasks

- [x] Fix form defaults: `backend` → `_DEFAULT_BACKEND`, `max_iterations` →
  `_DEFAULT_MAX_ITERATIONS`, `ci_check_wait_minutes` → `_DEFAULT_CI_WAIT_MINUTES`
  in both `enqueue_build_form` and `_build_form_redirect_query`
- [x] DRY `_is_running_in_docker()` → use `_TRUTHY_VALUES`
- [x] Move `import time` to top-level in `app.py`
- [x] Extract `_TOOL_SUMMARY_KEY_MAP` and `_TOOL_SUMMARY_STATIC` dispatch tables
  in `claude.py`, refactor `_summarize_tool()` to use them
- [x] Add 52 tests covering all changes
- [x] Update existing `__all__` tests to reflect new exports

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
