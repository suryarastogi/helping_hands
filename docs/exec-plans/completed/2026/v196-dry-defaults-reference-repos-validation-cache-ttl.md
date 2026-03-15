# v196 — DRY shared defaults, reference_repos validation, usage cache TTL

**Status:** Completed
**Date:** 2026-03-15

## Tasks

- [x] DRY shared defaults — extract `DEFAULT_BACKEND`, `DEFAULT_MAX_ITERATIONS`,
  `DEFAULT_CI_WAIT_MINUTES` constants in `server/constants.py`, reference from
  `app.py` (`BuildRequest`, `ScheduleRequest`, `ScheduleResponse`) and
  `schedules.py` (`ScheduledTask`, `from_dict`)
- [x] Add `max_length=MAX_REFERENCE_REPOS` validation to `reference_repos` in
  `BuildRequest` and `ScheduleRequest`
- [x] Extract `USAGE_CACHE_TTL_S = 300` named constant in `server/constants.py`,
  replace local `_USAGE_CACHE_TTL` in `app.py`
- [x] Add 27 new tests (7 constant values, 6 app defaults, 6 schedules defaults,
  5 reference_repos validation, 2 usage cache TTL, 1 __all__ update)
- [x] Update `__all__` in existing test (v179)

## Changes

### 1. DRY shared defaults (server/constants.py)
- Added `DEFAULT_BACKEND = "claudecodecli"`, `DEFAULT_MAX_ITERATIONS = 6`,
  `DEFAULT_CI_WAIT_MINUTES = 3.0` to `server/constants.py`
- `app.py` `BuildRequest`, `ScheduleRequest`, `ScheduleResponse` now reference
  shared constants instead of duplicated literals
- `schedules.py` `ScheduledTask` dataclass defaults and `from_dict()` fallbacks
  now reference shared constants instead of duplicated literals

### 2. reference_repos max_length validation
- Added `MAX_REFERENCE_REPOS = 10` to `server/constants.py`
- `BuildRequest.reference_repos` and `ScheduleRequest.reference_repos` now enforce
  `max_length=_MAX_REFERENCE_REPOS` via Pydantic `Field()`

### 3. Usage cache TTL named constant
- Added `USAGE_CACHE_TTL_S = 300` with docstring to `server/constants.py`
- Replaced local `_USAGE_CACHE_TTL = 300` in `app.py` with imported
  `_USAGE_CACHE_TTL_S` from shared constants

## Tests
- 27 new tests in `test_v196_dry_defaults_reference_repos_cache_ttl.py`
- 1 updated test in `test_v179_dry_github_url_server_constants.py` (`__all__` count)
- 4723 tests passing, 174 skipped
