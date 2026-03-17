# v250: Hand factory function + backend name constants

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

The backend→Hand if/elif dispatch chain is duplicated between `cli/main.py`
(lines 348–371) and `celery_app.py` (lines 826–867). Both locations:
- Map a backend name string to a Hand subclass
- Pass `config`, `repo_index`, and optionally `max_iterations`
- Handle `ModuleNotFoundError` with different messaging

Backend name strings (110 occurrences across 16 files) are bare string
literals with no shared constants.

## Tasks

- [x] Create `src/helping_hands/lib/hands/v1/hand/factory.py` with:
  - Backend name constants (`BACKEND_*`)
  - `SUPPORTED_BACKENDS` frozenset
  - `create_hand()` factory function
- [x] Wire `create_hand()` into `cli/main.py` (replacing if/elif chain)
- [x] Wire `create_hand()` into `celery_app.py` (replacing if/elif chain)
- [x] Update `server/constants.py` `DEFAULT_BACKEND` to use constant
- [x] Add comprehensive tests for `factory.py`
- [x] Verify all existing tests pass

## Completion criteria

- `create_hand()` is the single source of truth for backend→Hand mapping
- Backend name constants replace bare strings in both call sites
- All existing tests pass + new factory tests added
