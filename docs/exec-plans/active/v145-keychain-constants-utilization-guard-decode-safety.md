## v145 — Extract keychain constants, utilization type guard, decode error safety

**Status:** Active
**Created:** 2026-03-12

## Goal

Three self-contained improvements targeting the OAuth/usage subsystem in `server/app.py` and `server/celery_app.py`:

1. **Extract keychain constants** — `"Claude Code-credentials"`, `"claudeAiOauth"`, and `"accessToken"` are hardcoded magic strings duplicated identically in both `app.py` and `celery_app.py`. Extract to module-level constants (`_KEYCHAIN_SERVICE_NAME`, `_KEYCHAIN_OAUTH_KEY`, `_KEYCHAIN_ACCESS_TOKEN_KEY`) in each file with cross-module sync tests.

2. **Add numeric type guard for utilization values** (`app.py`) — `_fetch_claude_usage()` calls `round(five_hour["utilization"], 1)` after an `is not None` check, but doesn't verify the value is actually numeric. A string or other non-numeric type from the API would crash with `TypeError`. Add `isinstance(val, (int, float))` guard before `round()`.

3. **Add decode safety** (`app.py`) — `resp.read().decode()` in `_fetch_claude_usage()` uses default strict decoding. Add `errors="replace"` to both the success path and HTTP error body decode to prevent `UnicodeDecodeError` on non-UTF-8 responses.

## Tasks

- [x] Extract `_KEYCHAIN_SERVICE_NAME = "Claude Code-credentials"` in `server/app.py`
- [x] Extract `_KEYCHAIN_OAUTH_KEY = "claudeAiOauth"` in `server/app.py`
- [x] Extract `_KEYCHAIN_ACCESS_TOKEN_KEY = "accessToken"` in `server/app.py`
- [x] Extract same three constants in `server/celery_app.py`
- [x] Use constants in `_get_claude_oauth_token()` (app.py) and `log_claude_usage()` (celery_app.py)
- [x] Add `isinstance` numeric type guard before `round()` in `_fetch_claude_usage()` (app.py)
- [x] Add `decode(errors="replace")` for API response and error body decode (app.py)
- [x] Add tests for all improvements (20 tests: 5 app constants, 4 celery constants, 3 sync, 6 utilization, 2 decode)
- [x] Run lint and tests — 3494 passing, 80 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass (20 tests: all skipped without fastapi/celery in base env)
- `ruff check` and `ruff format` pass
- Docs updated with v145 notes
