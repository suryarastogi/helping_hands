# v195 — DRY git identity, browse max chars, and clone timeout

**Status:** Completed
**Date:** 2026-03-15

## Changes

### 1. DRY git identity constants (e2e.py → base.py)
- `_E2E_GIT_USER_NAME` and `_E2E_GIT_USER_EMAIL` in `e2e.py` now reference
  `_DEFAULT_GIT_USER_NAME` and `_DEFAULT_GIT_USER_EMAIL` from `base.py`
  instead of duplicating the string literals `"helping-hands[bot]"` and
  `"helping-hands-bot@users.noreply.github.com"`

### 2. DRY browse max chars constant (web.py → registry.py, mcp_server.py)
- Extracted `DEFAULT_BROWSE_MAX_CHARS = 12000` in `web.py` as the single source
- `browse_url()` default parameter now uses `DEFAULT_BROWSE_MAX_CHARS`
- `registry.py` browse_url call uses `web_tools.DEFAULT_BROWSE_MAX_CHARS`
- `mcp_server.py` `_DEFAULT_BROWSE_MAX_CHARS` now references `web_tools.DEFAULT_BROWSE_MAX_CHARS`
- Added to `web.py` `__all__` exports

### 3. DRY clone timeout (github_url.py → cli/main.py, celery_app.py)
- Extracted `GIT_CLONE_TIMEOUT_S = 120` to `github_url.py` as the single source
- `cli/main.py` imports `_GIT_CLONE_TIMEOUT_S` from `github_url`
- `celery_app.py` imports `_GIT_CLONE_TIMEOUT_S` from `github_url`
- Added to `github_url.py` `__all__` exports

## Tests
- 15 new tests (4 git identity, 6 browse max chars, 5 clone timeout)
- Updated 2 existing tests (`__all__` counts for web.py and github_url.py)
- 4715 tests passing, 156 skipped
