# v260: Unify truthy values and add env var helpers

## Problem

1. `_TRUTHY_VALUES | {"on"}` is duplicated as `_PR_TRUTHY_VALUES` (pr_description.py)
   and `_CLI_TRUTHY_VALUES` (cli/base.py) — identical sets defined independently.
2. `os.environ.get(name, "").strip()` appears 20+ times across the codebase with
   no shared helper.
3. `_is_truthy_env()` in config.py doesn't `.strip()` before checking, while
   most callers manually strip first.

## Changes

### 1. Add "on" to base `_TRUTHY_VALUES` (config.py)
- `frozenset({"1", "true", "yes", "on"})` — standard truthy value
- Update `_is_truthy_env()` to also `.strip()` the value before lowering
- Add `_get_env_stripped(name, default="")` helper

### 2. Remove derived truthy sets
- Remove `_PR_TRUTHY_VALUES` from pr_description.py
- Remove `_CLI_TRUTHY_VALUES` from cli/base.py
- Update `_TwoPhaseCLIHand._is_truthy()` to use `_TRUTHY_VALUES` directly

### 3. Simplify callers to use `_is_truthy_env()`
- `pr_description.py:_is_disabled()` → `_is_truthy_env(_DISABLE_ENV_VAR)`
- `e2e.py:_draft_pr_enabled()` → `_is_truthy_env("HELPING_HANDS_E2E_DRAFT_PR", "true")`
- `app.py:_is_running_in_docker()` → `_is_truthy_env("HELPING_HANDS_IN_DOCKER")`

### 4. Tests
- Test `_is_truthy_env` with "on", whitespace, and edge cases
- Test `_get_env_stripped` helper
- Test that removed constants no longer exist

## Files touched
- `src/helping_hands/lib/config.py`
- `src/helping_hands/lib/hands/v1/hand/pr_description.py`
- `src/helping_hands/lib/hands/v1/hand/cli/base.py`
- `src/helping_hands/lib/hands/v1/hand/e2e.py`
- `src/helping_hands/server/app.py`
- `tests/test_config.py` (new tests)
- `tests/test_pr_description.py` (update tests)
- `tests/test_cli_base.py` (update tests)

## Tasks

- [x] Add "on" to `_TRUTHY_VALUES` in config.py
- [x] Update `_is_truthy_env()` to strip whitespace
- [x] Add `_get_env_stripped()` helper
- [x] Remove `_PR_TRUTHY_VALUES` from pr_description.py
- [x] Remove `_CLI_TRUTHY_VALUES` from cli/base.py
- [x] Simplify `pr_description._is_disabled()` to use `_is_truthy_env()`
- [x] Simplify `E2EHand._draft_pr_enabled()` to use `_is_truthy_env()`
- [x] Simplify `app._is_running_in_docker()` to use `_is_truthy_env()`
- [x] Update `_TwoPhaseCLIHand._is_truthy()` to use `_TRUTHY_VALUES`
- [x] Update existing tests referencing removed constants
- [x] Add new tests for helpers and consumers
- [x] All tests pass

## Completion criteria

- `_TRUTHY_VALUES` is the single source of truth (includes "on")
- No `_PR_TRUTHY_VALUES` or `_CLI_TRUTHY_VALUES` constants exist
- `_is_truthy_env()` strips whitespace before checking
- `_get_env_stripped()` available as shared helper
- All tests pass

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17
**Tests:** 28 new (6083 passed, 270 skipped)
