# v202 — DRY truncation marker and PR metadata factory

**Status:** Completed
**Created:** 2026-03-15

## Problem

1. The truncation marker string `"...[truncated]"` is duplicated across 4 modules
   (base.py, celery_app.py, pr_description.py, cli/base.py — 5 usages total).

2. The PR metadata dict `{"pr_status": …, "pr_url": "", "pr_number": "",
   "pr_branch": "", "pr_commit": ""}` is duplicated in `base.py` (_finalize_repo_pr)
   and `cli/base.py` (_interrupted_pr_metadata).

## Tasks

- [x] Extract `_TRUNCATION_MARKER = "...[truncated]"` in `base.py`, replace 5× across 4 modules
- [x] Extract `_default_pr_metadata(*, auto_pr, pr_status)` factory in `base.py`, replace 2× dicts
- [x] Add tests for constant value, factory output, and cross-module import identity
- [x] Run lint + format + type check + tests
- [x] Update docs (Week-12, PLANS.md)

## Completion criteria

- All 5 truncation marker sites use the shared constant
- Both PR metadata dict constructions use the shared factory
- Tests pass, ruff clean, ty clean
