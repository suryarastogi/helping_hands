# v252: Backend lookup constants + factory coverage

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

1. `app.py` `_BACKEND_LOOKUP` (lines 620–631) uses bare string keys instead of
   the `BACKEND_*` constants from `factory.py` (introduced in v250).
2. `mcp_server.py` line 116 uses a bare `"codexcli"` default instead of
   `BACKEND_CODEXCLI`.
3. `factory.py` coverage is 79% — the LangGraph and Atomic creation paths
   (lines 106–111, 146–151) are uncovered because the optional extras are
   not installed in CI. Mock-based tests can cover these paths.

## Tasks

- [x] Replace `_BACKEND_LOOKUP` keys in `app.py` with `BACKEND_*` constants
- [x] Replace bare `"codexcli"` default in `mcp_server.py` with `BACKEND_CODEXCLI`
- [x] Add mock-based tests for `create_hand(BACKEND_BASIC_LANGGRAPH, ...)` path
- [x] Add mock-based tests for `create_hand(BACKEND_BASIC_ATOMIC, ...)` path
- [x] Add mock-based tests for `max_iterations` kwarg forwarding
- [x] Verify all existing tests pass + coverage improvement
- [x] Update ARCHITECTURE.md and docs

## Completion criteria

- `_BACKEND_LOOKUP` uses only `BACKEND_*` constants as keys
- `mcp_server.py` default uses `BACKEND_CODEXCLI`
- `factory.py` coverage ≥ 95%
- All existing tests pass
