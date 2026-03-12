## v141 — E2E marker constant, CLI PR number validation, Celery timeout constants

**Status:** Active
**Created:** 2026-03-12

## Goal

Three self-contained improvements:

1. **E2E marker filename constant** (`e2e.py`) — The string `"HELPING_HANDS_E2E.md"` is hardcoded inline in `run()`. Extract to a module-level constant `_E2E_MARKER_FILE` for discoverability and consistency with the project's constant extraction pattern.

2. **CLI `--pr-number` positive validation** (`cli/main.py`) — The `--pr-number` argument accepts any integer including negative/zero via `type=int` with no bounds check. Add post-parse validation to reject non-positive values before they reach the E2E hand (which would pass them to `get_pr()` and hit the v140 `ValueError` guard).

3. **Celery timeout constants** (`celery_app.py`) — Two remaining hardcoded timeout values: `timeout=5` in the Keychain subprocess call and `connect_timeout=5` in `psycopg2.connect()`. Extract to `_KEYCHAIN_TIMEOUT_S` and `_DB_CONNECT_TIMEOUT_S` module-level constants, matching the pattern used in `server/app.py` (v137).

## Tasks

- [x] Extract `_E2E_MARKER_FILE = "HELPING_HANDS_E2E.md"` in `e2e.py`
- [x] Add post-parse `--pr-number > 0` validation in `cli/main.py`
- [x] Extract `_KEYCHAIN_TIMEOUT_S = 5` and `_DB_CONNECT_TIMEOUT_S = 5` in `celery_app.py`
- [x] Add tests for all improvements (15 tests: 4 E2E constant, 4 PR validation, 7 Celery constants)
- [x] Run lint and tests — 3464 passing, 44 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass (15 tests: 8 passed, 7 skipped without celery)
- `ruff check` and `ruff format` pass
- Docs updated with v141 notes
