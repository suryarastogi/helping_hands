# v249 — Deduplicate env var constants between github_url.py and base.py

**Status:** Completed
**Created:** 2026-03-17

## Problem

`_ENV_GIT_TERMINAL_PROMPT` and `_ENV_GCM_INTERACTIVE` were defined identically in two
places:
- `src/helping_hands/lib/github_url.py` (lines 35–38) — canonical location
- `src/helping_hands/lib/hands/v1/hand/base.py` (lines 227–230) — duplicate

Both suppress interactive git credential prompts. The canonical home is `github_url.py`
(the shared GitHub URL helpers module). `base.py` should import from there.

## Tasks

- [x] Create this plan
- [x] Rename to public `ENV_GIT_TERMINAL_PROMPT`/`ENV_GCM_INTERACTIVE` in `github_url.py`
- [x] Add to `github_url.py` `__all__`
- [x] Replace duplicate definitions in `base.py` with imports from `github_url.py`
- [x] Update 3 existing test files with new `__all__` expectations
- [x] Update v241 test for renamed constants in `github_url.py`
- [x] Add AST-based test: no `_ENV_*` assignments in `base.py`
- [x] Add identity test: constants imported in `base.py` are the same objects as `github_url.py`
- [x] Add behavioral tests: `_push_noninteractive` still uses the constants correctly
- [x] Run full test suite + lint

## Completion criteria

- Zero `_ENV_GIT_TERMINAL_PROMPT = ` or `_ENV_GCM_INTERACTIVE = ` assignments in `base.py`
- `base.py` imports both from `github_url`
- All new tests pass
- Full test suite passes with no regressions
- Lint and format checks clean

## Changes

### `src/helping_hands/lib/github_url.py`
- Renamed `_ENV_GIT_TERMINAL_PROMPT` → `ENV_GIT_TERMINAL_PROMPT` (public)
- Renamed `_ENV_GCM_INTERACTIVE` → `ENV_GCM_INTERACTIVE` (public)
- Added both to `__all__`

### `src/helping_hands/lib/hands/v1/hand/base.py`
- Removed duplicate constant definitions (lines 224–231)
- Added imports: `ENV_GIT_TERMINAL_PROMPT as _ENV_GIT_TERMINAL_PROMPT` and
  `ENV_GCM_INTERACTIVE as _ENV_GCM_INTERACTIVE` from `github_url`

### `tests/test_v249_deduplicate_env_var_constants.py` (new)
- 16 tests across 8 test classes
- Identity tests (constants are same objects across modules)
- AST-based: no assignments of `_ENV_*` in `base.py`
- Canonical definition: exactly 1 assignment in `github_url.py`
- `__all__` export verification
- Import source verification (base.py imports from github_url)
- Behavioral: `_push_noninteractive` uses constants, no bare env strings
- Docstring presence in `github_url.py`

### `tests/test_github_url.py`, `tests/test_v179_*.py`, `tests/test_v210_*.py`
- Updated expected `__all__` sets to include `ENV_GCM_INTERACTIVE` and
  `ENV_GIT_TERMINAL_PROMPT`

### `tests/test_v241_metadata_envvar_constants.py`
- Updated `test_defines_env_constants` to check for `ENV_*` (public names)
  in `github_url.py` source

## Test results

- **16 new tests** (0 skipped)
- **5893 passed**, 249 skipped, 0 failures
- All lint/format checks pass
- 78.43% coverage
