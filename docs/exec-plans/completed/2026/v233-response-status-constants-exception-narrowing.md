# v233 — Response status constants, exception narrowing in log_claude_usage

**Created:** 2026-03-16
**Status:** Completed

## Goal

Two self-contained improvements across server modules:

1. **Extract response status constants** — `RESPONSE_STATUS_OK`, `RESPONSE_STATUS_ERROR`,
   `RESPONSE_STATUS_NA` to `server/constants.py`, replacing 10+ bare `"ok"`/`"error"`/`"na"`
   string literals in `celery_app.py` and `app.py` response dicts.
2. **Narrow `except Exception` handlers** in `log_claude_usage()`:
   - Keychain subprocess: `except (subprocess.CalledProcessError, OSError, TimeoutExpired)`
   - Usage API urllib: `except (URLError, OSError)`

## Tasks

- [x] Create this plan
- [x] Add `RESPONSE_STATUS_OK`, `RESPONSE_STATUS_ERROR`, `RESPONSE_STATUS_NA` to constants.py
- [x] Replace bare status strings in `celery_app.py` response dicts
- [x] Replace bare status strings in `app.py` health-check helpers
- [x] Narrow `except Exception` on keychain and urllib handlers
- [x] Add tests (22 new: all passed)
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All changes have tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/server/constants.py` — 3 new constants + `__all__` update
- `src/helping_hands/server/celery_app.py` — use shared constants, narrow exception handlers
- `src/helping_hands/server/app.py` — use shared constants in health checks and /health endpoint
- `tests/test_v233_response_status_constants_exception_narrowing.py` — 22 new tests
- `tests/test_v232_redbeat_constants_exception_narrowing.py` — `__all__` equality → superset check
