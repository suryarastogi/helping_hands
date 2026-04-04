# v357 — Extract Token Helpers & Add Tests

**Created:** 2026-04-04
**Status:** Active

## Goal

Extract pure helper functions from `server/app.py` into a new
`server/token_helpers.py` module that can be imported and tested without the
`fastapi` / `celery` server extras. This closes coverage gaps for
`_redact_token`, `_read_claude_credentials_file`, and `_get_claude_oauth_token`
which are currently unreachable in test environments lacking the server extra.

## Tasks

- [x] Create `server/token_helpers.py` with `redact_token`,
      `read_claude_credentials_file`, `get_claude_oauth_token`
- [x] Update `server/app.py` to import from `token_helpers` instead of
      defining locally
- [x] Add tests for `redact_token` (None, empty, short, long, exact boundary)
- [x] Add tests for `read_claude_credentials_file` (happy path, missing file,
      invalid JSON, OSError)
- [x] Add tests for `get_claude_oauth_token` (creds file hit, keychain
      fallback, keychain JSON, keychain raw JWT, keychain failure, both fail)
- [x] Move v356 to completed
- [x] Consolidate 2026-04-04 daily plans
- [x] Update Week-14, INTENT.md, PLANS.md
- [x] Run pytest, ruff check, ruff format — all clean
      (6795 passed, 271 skipped, 75.89% coverage)

## Completion criteria

- New `server/token_helpers.py` importable without server extras ✓
- ≥15 new tests for token helper functions ✓ (22 tests)
- All existing tests still pass ✓ (6795 passed)
- ruff check + format clean ✓
