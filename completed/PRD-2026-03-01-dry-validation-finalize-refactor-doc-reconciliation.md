# PRD: DRY Validation Utilities, Finalize Refactor & Doc Reconciliation

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Extract duplicated validation helpers into a shared module, refactor the longest function in the codebase, harden the last broad exception catch, improve documentation accuracy, and reconcile all doc surfaces.

---

## Problem Statement

The codebase is in excellent shape (579 tests, zero lint/format/type errors, 36 API pages). However, a targeted audit reveals several self-contained improvements:

1. **Code duplication**: `_parse_str_list`, `_parse_positive_int`, `_parse_optional_str` are identically duplicated between `iterative.py` (static methods) and `skills/__init__.py` (module functions). This violates DRY and creates a maintenance burden.

2. **Long function**: `_finalize_repo_pr` in `base.py` is 161 lines with nested try/finally blocks and environment variable manipulation. Extracting helpers improves readability and testability.

3. **Broad exception catch**: `_finalize_repo_pr` line 391 uses `except Exception` as a catch-all after specific `ValueError` and `RuntimeError` handlers. This should catch the remaining plausible types (`GithubException`, `OSError`) explicitly.

4. **Documentation formatting**: `docs/index.md` line 11 is a 1,438-character single line listing all lib API links. This is unreadable in raw markdown and creates poor diffs.

5. **Missing regex documentation**: Four complex regex patterns in `iterative.py` lack inline comments explaining their capture groups and expected formats.

6. **Obsidian drift**: Project Log W10 and Architecture.md need reconciliation with current work.

## Success Criteria

- [x] Shared validation module exists; both `iterative.py` and `skills/__init__.py` import from it
- [x] `_finalize_repo_pr` broken into smaller helpers (each <50 lines)
- [x] `except Exception` replaced with specific types in `base.py`
- [x] `docs/index.md` reformatted with multi-line structured list
- [x] Regex patterns in `iterative.py` have inline documentation
- [x] Obsidian vault reconciled (Architecture.md, Project Log W10)
- [x] All tests pass after changes

## Non-Goals

- Changing any runtime behavior or adding features
- Adding new tests (only verifying existing tests still pass)
- Refactoring `_invoke_cli_with_cmd` (complex but well-structured as-is)

---

## TODO

### 1. Extract shared validation utilities
- [x] Create `src/helping_hands/lib/validation.py` with `parse_str_list`, `parse_positive_int`, `parse_optional_str`
- [x] Update `skills/__init__.py` to import from `lib.validation` instead of defining locally
- [x] Update `iterative.py` to import from `lib.validation` instead of defining static methods
- [x] Verify all 579 tests still pass

### 2. Refactor `_finalize_repo_pr` in base.py
- [x] Extract `_push_with_non_interactive_env()` helper for env var save/restore + push
- [x] Extract `_create_pr_from_branch()` helper for PR title/body generation + creation
- [x] Verify all tests still pass

### 3. Replace broad exception in base.py
- [x] Replace `except Exception` (line 391) with `except (OSError, KeyError, AttributeError)` or similar based on what GitHub/git operations can actually raise

### 4. Reformat docs/index.md
- [x] Break line 11 into a structured multi-line list with one link per line

### 5. Document regex patterns in iterative.py
- [x] Add inline comments above `_EDIT_PATTERN`, `_READ_PATTERN`, `_READ_FALLBACK_PATTERN`, `_TOOL_PATTERN`

### 6. Reconcile Obsidian vault
- [x] Update Architecture.md with current changes
- [x] Update Project Log W10 with this PRD's work
- [x] Update Project todos.md if needed

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created after comprehensive audit (code, docs, tests, lint/format/type checks) |
| 2026-03-01 | Created `lib/validation.py` with shared parse helpers; updated `skills/__init__.py` to import from it; removed dead code static methods from `iterative.py` |
| 2026-03-01 | Refactored `_finalize_repo_pr` (161→45 lines) into `_push_with_non_interactive_env` and `_create_pr_from_branch` helpers |
| 2026-03-01 | Replaced `except Exception` with `except (OSError, KeyError, AttributeError)` in `base.py` |
| 2026-03-01 | Reformatted `docs/index.md` lib API list from single 1,438-char line to structured multi-line format |
| 2026-03-01 | Added inline regex pattern documentation to 4 patterns in `iterative.py` |
| 2026-03-01 | Created `docs/api/lib/validation.md` (37th API page); updated mkdocs.yml nav and docs/index.md |
| 2026-03-01 | Updated Obsidian Architecture.md, Project todos.md, Project Log W10 |
| 2026-03-01 | All 579 tests pass, ruff lint + format + type checks pass. PRD complete |
