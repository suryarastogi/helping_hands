# v257 — Centralize DEFAULT_MAX_ITERATIONS constant

**Status:** Completed
**Created:** 2026-03-17

## Problem

`max_iterations: int = 6` appears as a bare literal default in 5 places:
- `iterative.py` `_BasicIterativeHand.__init__()` (line 122)
- `iterative.py` `BasicLangGraphHand.__init__()` (line 915)
- `iterative.py` `BasicAtomicHand.__init__()` (line 1106)
- `mcp_server.py` `run_hand()` (line 121)
- `celery_app.py` `build()` (line 585)

Meanwhile, `server/constants.py` already defines `DEFAULT_MAX_ITERATIONS = 6` and
uses it in `app.py`, `schedules.py`, etc. The lib-layer code can't import from
`server/constants.py` (architecture: server depends on lib, not vice versa).

## Tasks

- [x] Define `DEFAULT_MAX_ITERATIONS: int = 6` in `iterative.py` alongside
  `_MAX_ITERATIONS = 1000`, add to `__all__`
- [x] Use it in all 3 `__init__` signatures in `iterative.py`
- [x] Update `server/constants.py` to re-export from `iterative.py` (canonical source)
- [x] Update `server/mcp_server.py` to import `DEFAULT_MAX_ITERATIONS`
- [x] Update `server/celery_app.py` to import and use `_DEFAULT_MAX_ITERATIONS`
- [x] Update `test_v161_all_exports.py` `__all__` count (2 → 3)
- [x] Write AST-based tests verifying no bare `6` remains as max_iterations default
- [x] Run full test suite — 6002 passed, 270 skipped

## Completion criteria

- No bare `6` literal remains as a `max_iterations` default in any source file
- `server/constants.py` re-exports the same object (identity) from `iterative.py`
- All existing tests continue to pass
- New tests cover value, type, identity, AST checks, and init signatures

## Files modified

- `src/helping_hands/lib/hands/v1/hand/iterative.py`
- `src/helping_hands/server/constants.py`
- `src/helping_hands/server/mcp_server.py`
- `src/helping_hands/server/celery_app.py`
- `tests/test_v161_all_exports.py`
- `tests/test_v257_centralize_default_max_iterations.py`
