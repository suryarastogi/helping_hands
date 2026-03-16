# v226 — DRY _run_bash_script, prompt builder type guards

**Created:** 2026-03-16
**Date:** 2026-03-16
**Status:** Completed

## Goal

Two self-contained improvements:

1. DRY `_run_bash_script()` in `registry.py` — replace manual `isinstance` checks with `_parse_optional_str()` for consistency with other runner wrappers
2. Add `require_non_empty_string()` type guards to `_build_prompt()` and `_build_commit_message_prompt()` in `pr_description.py` — defensive validation on private helpers whose callers already validate some (but not all) params

## Tasks

- [x] Replace manual isinstance checks in `_run_bash_script()` with `_parse_optional_str()`
- [x] Add `require_non_empty_string()` guards to `_build_prompt()` for `diff` and `backend`
- [x] Add `require_non_empty_string()` guards to `_build_commit_message_prompt()` for `diff` and `backend`
- [x] Write tests for new validation paths
- [x] Run ruff + ty + pytest
- [x] Update docs

## Changes

### `src/helping_hands/lib/meta/tools/registry.py`

- **`_run_bash_script()`**: Replaced 4-line manual `isinstance` checks for `script_path` and `inline_script` with `_parse_optional_str(payload, key=...)`. Gets whitespace stripping for free — whitespace-only values now normalize to `None` and hit the mutual-exclusion guard early.

### `src/helping_hands/lib/hands/v1/hand/pr_description.py`

- **`_build_prompt()`**: Added `require_non_empty_string(diff, "diff")` and `require_non_empty_string(backend, "backend")` type guards. Previously, passing `None` for `diff` would silently produce `"```diff\nNone\n```"` in the prompt.
- **`_build_commit_message_prompt()`**: Same type guards for `diff` and `backend`.

### Tests

- **`tests/test_v226_bash_runner_dry_prompt_builder_guards.py`**: 23 tests across 3 classes:
  - `TestRunBashScriptDry` (7): source consistency, non-string rejection, whitespace-only normalization, bool/list rejection
  - `TestBuildPromptTypeGuards` (9): source consistency, None/int/empty/whitespace diff, None/int/empty backend, valid pass-through
  - `TestBuildCommitMessagePromptTypeGuards` (7): source consistency, None/int/empty diff, None/empty backend, valid pass-through

## Completion criteria

- `_run_bash_script` source contains `_parse_optional_str` and no manual `isinstance` checks
- `_build_prompt(diff=None, ...)` raises `TypeError`
- `_build_prompt(diff="", ...)` raises `ValueError`
- `_build_commit_message_prompt(backend=None, ...)` raises `TypeError`
- All existing tests pass, new tests cover all changes

## Results

- **23 new tests**
- **5462 passed, 219 skipped**, coverage 78.76%
