# v389 — Fix Test Failures & Code Quality Improvements

**Created:** 2026-04-05
**Status:** Completed

## Goal

Fix 5 failing tests and improve code quality with targeted improvements:
1. Fix `isinstance` syntax consistency in `command.py`
2. Fix `update_pr` test patching for PyGithub `NotSet` sentinel
3. Fix doc structure tests (versioned plans missing Status field, PLANS.md test counts)
4. Add docstrings to conflict resolution helpers in `cli/base.py`
5. Narrow broad `except Exception` catches where safe

## Completion criteria

- All 5 previously-failing tests pass
- `GithubException` replaces broad `except Exception` in label removal
- Test added for non-GithubException propagation
- Full test suite passes with 0 failures
- INTENT.md, PLANS.md, and daily consolidation updated

## Tasks

- [x] Fix `_normalize_args` isinstance syntax in `command.py:88`
- [x] Fix `_patch_notset` in `test_v354` to patch `github.GithubObject.NotSet`
- [x] Fix versioned plans missing `**Status:**` field
- [x] Fix PLANS.md entries missing test counts
- [x] Narrow `except Exception` in `github.py` label removal to `GithubException`
- [x] Add test for non-GithubException propagation
- [x] Run tests to verify all failures resolved
- [x] Update INTENT.md, PLANS.md, daily consolidation

## Changes

### command.py
- Line 88: `list | tuple` → `(list, tuple)` for consistency with isinstance conventions

### test_v354_remaining_edge_case_coverage.py
- Fix `_patch_notset` to patch `github.GithubObject.NotSet` (where `update_pr` imports from)

### github.py
- Import `GithubException` and narrow `except Exception` to `except GithubException`

### test_github.py
- Update `test_silently_handles_missing_label` to raise `GithubException`
- Add `test_propagates_non_github_exceptions` verifying `OSError` propagates

### docs
- Fix `**Status:**` format in v388 plan
- Fix PLANS.md v385 entry test count format
