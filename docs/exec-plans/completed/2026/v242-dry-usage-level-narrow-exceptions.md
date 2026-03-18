# v242 — DRY usage level extraction and narrow exception handlers in app.py

**Status:** completed
**Created:** 2026-03-16
**Completed:** 2026-03-16

## Motivation

`_fetch_claude_usage()` in `server/app.py` has two nearly identical 12-line blocks
for extracting Session and Weekly usage levels from the API response. Extracting a
shared `_extract_usage_level()` helper eliminates this duplication.

Additionally, three `except Exception` handlers in `app.py` were narrowed to
specific exception types.

## Changes

### Code changes

- **Extracted `_extract_usage_level()`** helper in `app.py` — replaces 2× 12-line
  inline blocks (Session + Weekly) with a shared helper that takes `(data, key, name)`
  and returns `ClaudeUsageLevel | None`
- **Replaced inline blocks** in `_fetch_claude_usage()` with a 3-line loop calling
  the new helper
- **Narrowed `except Exception`** in `_get_claude_oauth_token()` to
  `(subprocess.SubprocessError, OSError)` — only `subprocess.run()` is wrapped
- **Narrowed `except Exception`** in `_fetch_claude_usage()` outer handler to
  `(urllib_error.URLError, OSError, json.JSONDecodeError)` — covers URL/network/JSON
  errors from `urllib_request.urlopen()` + `json.loads()`
- **Narrowed `except Exception`** in `_fetch_claude_usage()` inner handler (HTTP
  error body read) to `(OSError, UnicodeDecodeError)`
- **Updated v145 test** — `test_source_uses_isinstance` now inspects
  `_extract_usage_level` instead of `_fetch_claude_usage` (isinstance moved to helper)

### Tasks completed

- [x] Extract `_extract_usage_level()` helper in app.py
- [x] Narrow `except Exception` in `_get_claude_oauth_token()`
- [x] Narrow `except Exception` in `_fetch_claude_usage()` (outer + inner)
- [x] Add tests for `_extract_usage_level()` (12 tests)
- [x] Add tests for narrowed exception handlers (11 tests)
- [x] Update PLANS.md

## Test results

- 23 new tests added (all passed)
- 6754 passed, 2 skipped (no regressions)
- All lint/format checks pass

## Completion criteria

- [x] All tasks checked
- [x] `uv run pytest` passes with no new failures
- [x] `uv run ruff check .` passes
- [x] `uv run ruff format --check .` passes
