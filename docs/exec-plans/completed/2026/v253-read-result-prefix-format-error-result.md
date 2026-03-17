# v253: _READ_RESULT_PREFIX constant, _format_error_result prefix-based refactor

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

1. The string `"@@READ_RESULT"` appears as a bare literal in an f-string at
   `iterative.py` line 499 with no shared constant. `_TOOL_RESULT_PREFIX` was
   extracted in v252 but the parallel `@@READ_RESULT` prefix was missed.
2. `_format_error_result` at line 509 constructs `@@{tag}_RESULT:` dynamically
   from a string tag (`"READ"` × 4 calls, `"TOOL"` × 2 calls). These 6 bare
   tag strings have no constants and the method doesn't leverage the existing
   `_TOOL_RESULT_PREFIX` or the new `_READ_RESULT_PREFIX`.

## Tasks

- [x] Add `_READ_RESULT_PREFIX = "@@READ_RESULT"` constant to `iterative.py`
- [x] Replace bare `"@@READ_RESULT"` f-string at line 499 with `_READ_RESULT_PREFIX`
- [x] Refactor `_format_error_result` to accept a `prefix` str instead of `tag`
- [x] Update all 6 call sites: 4 × `_READ_RESULT_PREFIX`, 2 × `_TOOL_RESULT_PREFIX`
- [x] Add tests for `_READ_RESULT_PREFIX` (value, type, docstring, AST source check)
- [x] Add tests for refactored `_format_error_result` (both prefixes, format output)
- [x] Update v228 tests to use prefix constants instead of bare tag strings
- [x] Update PLANS.md, Week-12.md

## Completion criteria

- `_READ_RESULT_PREFIX` is the single source of truth for the read result block prefix
- `_format_error_result` uses prefix constants instead of dynamic tag construction
- No bare `"@@READ_RESULT"` or `"READ"`/`"TOOL"` tag strings remain in code paths
- All existing tests pass + new tests added
