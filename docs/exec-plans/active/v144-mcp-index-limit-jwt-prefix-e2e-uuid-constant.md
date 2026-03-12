## v144 — MCP index file limit, JWT token prefix constant, E2E UUID hex length reuse

**Status:** Active
**Created:** 2026-03-12

## Goal

Three self-contained improvements continuing the constant extraction and DRY patterns:

1. **Extract `_INDEX_FILES_LIMIT = 200`** (`mcp_server.py`) — `index_repo()` uses hardcoded `idx.files[:200]` to limit file listing output. Extract to a module-level constant for discoverability and consistency with the project's constant extraction pattern (v135-v143).

2. **Extract `_JWT_TOKEN_PREFIX = "ey"`** (`server/app.py` and `server/celery_app.py`) — Both `_get_claude_oauth_token()` and `log_claude_usage()` use `raw.startswith("ey")` as a fallback JWT detection heuristic. The magic string `"ey"` is duplicated across both modules. Extract to a module-level constant in each file (modules don't import each other's internals per architecture rules) with cross-module sync test.

3. **Import `_UUID_HEX_LENGTH` from `base.py`** in `e2e.py` — `run()` uses `hand_uuid[:8]` for branch naming, duplicating the `_UUID_HEX_LENGTH = 8` constant already defined in `base.py`. Import and reuse to maintain DRY consistency.

## Tasks

- [x] Extract `_INDEX_FILES_LIMIT = 200` in `mcp_server.py` and use in `index_repo()`
- [x] Extract `_JWT_TOKEN_PREFIX = "ey"` in `server/app.py` and use in `_get_claude_oauth_token()`
- [x] Extract `_JWT_TOKEN_PREFIX = "ey"` in `server/celery_app.py` and use in `log_claude_usage()`
- [x] Import `_UUID_HEX_LENGTH` from `base.py` in `e2e.py` and use in branch naming
- [x] Add tests for all improvements (15 tests: 4 MCP, 4 app.py, 4 celery_app.py, 3 E2E)
- [x] Run lint and tests — 3494 passing, 60 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass (15 tests: 7 passed, 8 skipped without fastapi/celery)
- `ruff check` and `ruff format` pass
- Docs updated with v144 notes
