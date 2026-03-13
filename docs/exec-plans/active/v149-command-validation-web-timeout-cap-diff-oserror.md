## v149 — Empty command validation, web timeout cap, _get_diff OSError handling

**Status:** Active
**Created:** 2026-03-13

## Goal

Three self-contained improvements:

1. **Empty command list validation in `_run_command()`** (`command.py`) — `_run_command()` does not validate that the `command` list is non-empty. An empty list would cause `IndexError` at `command[0]` in the `FileNotFoundError` handler (line 112). Add explicit `ValueError` guard.

2. **Maximum timeout cap for web tools** (`web.py`) — `search_web()` and `browse_url()` validate `timeout_s > 0` but don't cap it. Unreasonably large values (e.g. 3600+) could cause long hangs. Add `_MAX_WEB_TIMEOUT_S` constant (300s) with warning log when clamping, consistent with `_MAX_GIT_TIMEOUT` pattern in `github.py`.

3. **OSError handling in `_get_diff`/`_get_uncommitted_diff`** (`pr_description.py`) — Both functions catch `FileNotFoundError` for missing git, but not broader `OSError` (e.g. permission denied on git binary, broken symlink). Add `OSError` catch with debug logging and empty-string return, consistent with existing `FileNotFoundError` handling.

## Tasks

- [x] Add empty command list validation in `_run_command()` in `command.py`
- [x] Add `_MAX_WEB_TIMEOUT_S = 300` constant in `web.py`
- [x] Add timeout clamping with warning log in `search_web()` and `browse_url()`
- [x] Add `OSError` catch in `_get_diff()` (both subprocess calls) in `pr_description.py`
- [x] Add `OSError` catch in `_get_uncommitted_diff()` (both subprocess calls) in `pr_description.py`
- [x] Add tests for empty command validation (3 tests: empty list, single-element, error-before-timeout)
- [x] Add tests for web timeout cap (8 tests: constant value/type/sign, search over/at/below max, browse over/at max)
- [x] Add tests for _get_diff/_get_uncommitted_diff OSError handling (4 tests: OSError in each subprocess call)
- [x] Run lint and tests — 3597 passing, 80 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-12)

## Completion criteria

- All new tests pass (15 new tests)
- `ruff check` and `ruff format` pass
- Docs updated with v149 notes
