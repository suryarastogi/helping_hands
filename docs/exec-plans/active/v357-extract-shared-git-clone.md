# v357 — Extract Shared Git Clone Utility

**Created:** 2026-04-04
**Status:** Active

## Goal

Eliminate duplicated `git clone` subprocess logic between `cli/main.py` and
`server/celery_app.py` by extracting a shared `run_git_clone()` function into
`lib/github_url.py` (which already houses all git-related URL/env helpers).

Both modules previously duplicated:
- `subprocess.run(["git", "clone", ...])` with timeout handling
- `TimeoutExpired` → `ValueError` conversion
- Non-zero exit code error formatting with credential redaction
- `_github_clone_url()` one-line wrapper around `build_clone_url()`

## Tasks

- [x] Add `run_git_clone()` to `lib/github_url.py` with configurable depth and
      `no_single_branch` flag; update `__all__`
- [x] Update `cli/main.py` `_run_git_clone` to delegate to shared function;
      remove unused imports (`TimeoutExpired`, `_DEFAULT_CLONE_DEPTH`,
      `_GIT_CLONE_TIMEOUT_S`, `_git_noninteractive_env`, `_redact_sensitive`,
      `_DEFAULT_CLONE_ERROR_MSG`)
- [x] Update `server/celery_app.py` `_resolve_repo_path` and reference repo
      cloning to use `run_git_clone()`; remove `_redact_sensitive`,
      `_GIT_CLONE_TIMEOUT_S`, `_DEFAULT_CLONE_ERROR_MSG`,
      `_git_noninteractive_env` imports
- [x] Add 13 tests for `run_git_clone()` in `test_github_url.py`
      (success, timeout, nonzero exit, empty stderr, credential redaction,
      default depth, custom depth, no_single_branch true/false,
      noninteractive env, timeout value, docstring)
- [x] Update test imports across 4 test files to reference new locations
- [x] Move completed v356 plan, update INTENT.md, PLANS.md, Week-14
- [x] Run pytest, ruff check, ruff format — all clean
      (6789 passed, 267 skipped, 75.48% coverage)

## Completion criteria

- Zero duplicated `subprocess.run(["git", "clone", ...])` patterns ✓
- All existing tests still pass ✓ (6789 passed)
- New shared function has ≥90% branch coverage ✓ (100% — all branches tested)
- ruff check + format clean ✓
