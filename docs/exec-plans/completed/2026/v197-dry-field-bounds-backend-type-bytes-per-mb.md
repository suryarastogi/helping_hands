# v197 — DRY field validation bounds, BackendName type reuse, bytes-per-MB constant

**Status:** Completed
**Date:** 2026-03-15

## Tasks

- [x] Extract field validation bound constants to `server/constants.py`:
  `MAX_ITERATIONS_UPPER_BOUND`, `MIN_CI_WAIT_MINUTES`, `MAX_CI_WAIT_MINUTES`,
  `MAX_REPO_PATH_LENGTH`, `MAX_PROMPT_LENGTH`, `MAX_MODEL_LENGTH`,
  `MAX_GITHUB_TOKEN_LENGTH`
- [x] Use `BackendName` type alias in `BuildRequest.backend` field instead of
  duplicated inline `Literal[...]`; move `BackendName` above `BuildRequest`;
  add `BackendName` to `app.py` `__all__`
- [x] Extract `_BYTES_PER_MB = 1024 * 1024` in `filesystem.py`, replace inline
  `1024 * 1024` in file size error formatting
- [x] Add tests for all new constants (value, type, field constraint sync)
- [x] Update `__all__` in `server/constants.py` (7 new exports)
- [x] Update existing `__all__` tests in v179 and v196 test files
- [x] Update docs (PLANS.md)

## Changes

### 1. DRY field validation bound constants (server/constants.py)
- Added 7 constants: `MAX_ITERATIONS_UPPER_BOUND = 100`,
  `MIN_CI_WAIT_MINUTES = 0.5`, `MAX_CI_WAIT_MINUTES = 30.0`,
  `MAX_REPO_PATH_LENGTH = 500`, `MAX_PROMPT_LENGTH = 50_000`,
  `MAX_MODEL_LENGTH = 200`, `MAX_GITHUB_TOKEN_LENGTH = 500`
- `BuildRequest` and `ScheduleRequest` now reference shared constants instead
  of duplicated literals in all `Field()` definitions

### 2. BackendName type alias deduplication
- Moved `BackendName = Literal[...]` above `BuildRequest` class
- `BuildRequest.backend` now uses `BackendName` instead of inline `Literal`
  (was the only place with a duplicated backend list)
- Added `BackendName` to `app.py` `__all__`

### 3. _BYTES_PER_MB constant (filesystem.py)
- Extracted `_BYTES_PER_MB = 1024 * 1024` module-level constant
- `_MAX_FILE_SIZE_BYTES` now expressed as `10 * _BYTES_PER_MB`
- File size error formatting uses `_BYTES_PER_MB` instead of inline calculation

## Tests
- 33 new tests in `test_v197_dry_field_bounds_backend_type_bytes_per_mb.py`
  (10 constant value/type, 1 __all__, 7 BuildRequest field bounds,
  7 ScheduleRequest field bounds, 4 BackendName, 4 _BYTES_PER_MB)
- 2 updated tests (v179 + v196 `__all__` expected sets)
- 1 updated test (v161 app.py `__all__` count: 17 → 18)
- 4738 tests total (15 passed + 18 skipped in new file), 4736 passed overall, 192 skipped
