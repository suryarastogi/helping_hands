## v142 — Extract remaining magic numbers and add repo.py PermissionError handling

**Status:** Active
**Created:** 2026-03-12

## Goal

Four self-contained improvements continuing the constant extraction and robustness hardening patterns:

1. **Server app preview truncation constants** (`server/app.py`) — Two hardcoded slice limits in `_fetch_claude_usage()`: `[:200]` for HTTP error body preview and `[:300]` for usage data preview. Extract to `_HTTP_ERROR_BODY_PREVIEW_LENGTH` and `_USAGE_DATA_PREVIEW_LENGTH` module-level constants.

2. **CLI base hook/display constants** (`cli/base.py`) — Two hardcoded values: `3000` character limit for hook error output truncation in `_build_hook_fix_prompt()` and `[:8]` git ref display truncation in `_poll_ci_checks()`. Extract to `_HOOK_ERROR_TRUNCATION_LIMIT` and `_GIT_REF_DISPLAY_LENGTH` module-level constants.

3. **Docker sandbox naming constants** (`docker_sandbox_claude.py`) — Two hardcoded values in `_resolve_sandbox_name()`: `[:30]` sandbox name max length and `[:8]` UUID hex truncation. Extract to `_SANDBOX_NAME_MAX_LENGTH` and `_SANDBOX_UUID_HEX_LENGTH` module-level constants.

4. **RepoIndex PermissionError handling** (`repo.py`) — `from_path()` uses `path.rglob("*")` without catching `PermissionError`, which crashes on directories with restricted permissions. Add try-except with warning log and graceful skip.

## Tasks

- [x] Extract `_HTTP_ERROR_BODY_PREVIEW_LENGTH = 200` and `_USAGE_DATA_PREVIEW_LENGTH = 300` in `server/app.py`
- [x] Extract `_HOOK_ERROR_TRUNCATION_LIMIT = 3000` and `_GIT_REF_DISPLAY_LENGTH = 8` in `cli/base.py`
- [x] Extract `_SANDBOX_NAME_MAX_LENGTH = 30` and `_SANDBOX_UUID_HEX_LENGTH = 8` in `docker_sandbox_claude.py`
- [x] Add PermissionError handling in `RepoIndex.from_path()` with warning log
- [x] Add tests for all improvements (26 tests: 8 server/app, 8 cli/base, 7 docker sandbox, 3 repo)
- [x] Run lint and tests — 3480 passing, 52 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass (26 tests: 18 passed, 8 skipped without fastapi)
- `ruff check` and `ruff format` pass
- Docs updated with v142 notes
