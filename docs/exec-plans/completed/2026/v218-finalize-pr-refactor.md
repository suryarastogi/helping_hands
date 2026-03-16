# v218 — Extract _create_new_pr() and DRY PR description generation

**Status:** Completed
**Created:** 2026-03-16

## Motivation

`_finalize_repo_pr()` in `base.py` is 194 lines — the longest method in the
Hand hierarchy. The "create new PR" path (lines 1053–1135) duplicates the
commit-message → push → PR-description → create-PR pattern already present in
`_create_pr_for_diverged_branch()` and `_push_to_existing_pr()`.

Extracting a `_create_new_pr()` helper:
- Reduces `_finalize_repo_pr()` to a clean orchestrator (~80 lines)
- Makes new-PR creation independently testable
- DRYs the repeated "generate description, fall back to generic" pattern into
  `_generate_pr_title_and_body()` (used by 3 call sites)

## Tasks

- [x] Extract `_generate_pr_title_and_body()` helper (shared by 3 methods)
- [x] Extract `_create_new_pr()` from `_finalize_repo_pr()`
- [x] Add unit tests for `_generate_pr_title_and_body()`
- [x] Add unit tests for `_create_new_pr()`
- [x] Run ruff + ty + pytest
- [x] Update docs

## Completion criteria

- `_finalize_repo_pr()` reduced below 120 lines
- All existing tests pass
- New tests cover extracted methods
- Quality gates green
