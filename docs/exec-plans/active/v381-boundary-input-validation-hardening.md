# v381 — Boundary Input Validation Hardening

**Created:** 2026-04-05
**Status:** Active

## Goal

Harden input validation at three module boundaries where invalid input
currently produces confusing low-level errors (KeyError, AttributeError)
instead of clear, actionable error messages.

## Context

The codebase has excellent coverage (99.93%) and strong validation helpers
(`require_non_empty_string`, `require_positive_int`, etc.). However, three
boundary functions still rely on implicit assumptions rather than explicit
guards:

1. `resolve_hand_model()` uses bare `PROVIDERS[key]` at lines 122 and 146
   — a missing provider raises `KeyError` instead of a clear message.
2. `run_git_clone()` accepts `depth` as `int` but doesn't validate it's
   positive — negative/zero values produce confusing git errors.
3. `RepoIndex.from_path()` doesn't validate that `path` is a `Path`
   instance — a non-Path input raises `AttributeError` on `.is_dir()`.

## Tasks

- [x] Create active plan v381
- [x] Add defensive `.get()` + RuntimeError to `resolve_hand_model()` (lines 122, 146)
- [x] Add `require_positive_int` validation for `depth` in `run_git_clone()`
- [x] Add `isinstance(path, Path)` type guard to `RepoIndex.from_path()`
- [x] Add tests for each new validation path (10 tests: 4 model_provider + 3 github_url + 3 repo)
- [x] Move v380 to completed, update PLANS.md, INTENT.md, consolidation docs

## Completion criteria

- All three functions raise clear, typed errors on invalid input
- Tests cover every new error path
- Existing tests still pass
- Docs updated

## Files changed

- `src/helping_hands/lib/hands/v1/hand/model_provider.py`
- `src/helping_hands/lib/github_url.py`
- `src/helping_hands/lib/repo.py`
- `tests/test_hand_model_provider.py`
- `tests/test_github_url.py`
- `tests/test_repo.py`
- `docs/exec-plans/active/v381-boundary-input-validation-hardening.md`
- `docs/PLANS.md`
- `INTENT.md`
- `docs/exec-plans/completed/2026/2026-04-05.md`
- `docs/exec-plans/completed/2026/Week-14.md`
