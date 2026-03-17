# v252: _TOOL_RESULT_PREFIX, _GOOSE_BUILTIN_FLAG, _CLAUDE_CLI_NAME constants

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

1. The string `"@@TOOL_RESULT"` appears 3 times as a bare literal in f-strings
   across `iterative.py` (lines 568, 607, 634) with no shared constant.
2. The string `"--with-builtin"` appears 5 times as a bare literal in
   `goose.py` (lines 89, 91, 94, 123, 144) with no shared constant.
3. The string `"claude"` appears 4 times as a bare literal in `claude.py`
   (lines 321, 322, 394, 442) with no shared constant.

## Tasks

- [x] Add `_TOOL_RESULT_PREFIX` constant to `iterative.py`
- [x] Replace 3 bare `"@@TOOL_RESULT"` f-string prefixes with `_TOOL_RESULT_PREFIX`
- [x] Add `_GOOSE_BUILTIN_FLAG` constant to `goose.py`
- [x] Replace 5 bare `"--with-builtin"` literals with `_GOOSE_BUILTIN_FLAG`
- [x] Add `_CLAUDE_CLI_NAME` constant to `claude.py`
- [x] Replace 4 bare `"claude"` literals with `_CLAUDE_CLI_NAME`
- [x] Add tests for all 3 new constants (values, types, AST source checks)
- [x] Update PLANS.md, Week-12.md

## Completion criteria

- `_TOOL_RESULT_PREFIX` is the single source of truth for the tool result block prefix
- `_GOOSE_BUILTIN_FLAG` is the single source of truth for the Goose builtin flag
- `_CLAUDE_CLI_NAME` is the single source of truth for the Claude CLI binary name
- No bare `"@@TOOL_RESULT"`, `"--with-builtin"`, or `"claude"` literals remain in code paths
- All existing tests pass + new tests added
