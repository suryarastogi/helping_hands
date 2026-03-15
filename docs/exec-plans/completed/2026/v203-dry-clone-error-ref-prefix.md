# v203 — DRY clone error fallback and reference repo prefix

**Status:** Completed
**Created:** 2026-03-15

## Problem

1. The fallback error message `"unknown git clone error"` is duplicated in
   `cli/main.py` (line 449) and `celery_app.py` (line 197). A shorter variant
   `"unknown error"` appears in the reference-repo clone paths of both modules
   (cli/main.py line 498, celery_app.py line 700).

2. The reference repo temp-directory prefix pattern
   `f"helping_hands_ref_{spec.replace('/', '_')}_"` is duplicated between
   `cli/main.py` (line 473) and `celery_app.py` (line 679).

## Tasks

- [x] Add `UNKNOWN_CLONE_ERROR` constant and `ref_repo_tmp_prefix()` helper to `github_url.py`
- [x] Update `cli/main.py` to import and use the shared constant and helper
- [x] Update `celery_app.py` to import and use the shared constant and helper
- [x] Add tests: constant value, helper output, cross-module import identity
- [x] Run lint + format + type check + tests
- [x] Update docs (Week-12, PLANS.md)

## Completion criteria

- All clone error fallback sites use the shared constant
- Both reference repo prefix constructions use the shared helper
- Tests pass, ruff clean, ty clean
