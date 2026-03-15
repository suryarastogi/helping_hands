# v212 — Extract `run_git_clone()` helper to `github_url.py`

**Status:** Completed
**Created:** 2026-03-15

## Summary

Consolidate the 4 duplicated git-clone subprocess patterns (cli/main.py ×2,
celery_app.py ×2) into a single `run_git_clone()` function in `github_url.py`.

Each call site repeats the same ~12-line pattern: build a `["git", "clone", ...]`
command, call `subprocess.run()` with `capture_output`, `text`, `check=False`,
`noninteractive_env()`, and `GIT_CLONE_TIMEOUT_S`, then handle `TimeoutExpired`
and non-zero return codes with credential redaction.

Also:
- Move `DEFAULT_CLONE_DEPTH = 1` to `github_url.py` (currently only in cli/main.py)
- Remove now-unnecessary `subprocess`/`TimeoutExpired` imports from cli/main.py
- Remove duplicated `_github_clone_url()` wrapper functions from both modules

## Tasks

- [x] Add `DEFAULT_CLONE_DEPTH` constant and `run_git_clone()` function to `github_url.py`
- [x] Update `cli/main.py` to use `run_git_clone()`, remove subprocess imports
- [x] Update `celery_app.py` to use `run_git_clone()`
- [x] Add versioned tests in `tests/test_v212_dry_run_git_clone.py`
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All 4 clone call sites use `run_git_clone()` instead of inline subprocess
- `_github_clone_url()` wrappers removed from both modules
- `_DEFAULT_CLONE_DEPTH` removed from cli/main.py (shared from github_url.py)
- Versioned tests cover the new helper
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
