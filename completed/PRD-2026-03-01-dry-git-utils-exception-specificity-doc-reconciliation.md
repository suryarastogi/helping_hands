# PRD: DRY Git Utilities, Exception Specificity & Doc Reconciliation

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Eliminate duplicate git/repo helper functions across CLI and server modules, replace remaining bare `except Exception` patterns with specific exception types, and reconcile all documentation surfaces.

---

## Problem Statement

The codebase has **four helper functions duplicated verbatim** between `cli/main.py` and `server/celery_app.py`:
- `_github_clone_url()` — builds token-authenticated clone URLs
- `_git_noninteractive_env()` — disables interactive git prompts
- `_redact_sensitive()` — masks tokens in error messages (also duplicated in `github.py`)
- `_repo_tmp_dir()` — resolves temp directory for cloned repos

Additionally, `server/app.py` has **3 health check functions** that catch bare `except Exception` instead of specific exception types, contrary to the AGENT.md convention on exception specificity.

## Success Criteria

- [x] Four duplicate helpers extracted to a shared `lib/git_utils.py` module
- [x] `cli/main.py` and `server/celery_app.py` import from shared module instead of defining duplicates
- [x] `github.py` `_redact_sensitive()` consolidated with shared module
- [x] 3 health check `except Exception` patterns in `server/app.py` replaced with specific types
- [x] All 624 tests pass, lint/format clean
- [x] Obsidian vault, AGENT.md, and cross-surface docs reconciled

## Non-Goals

- Refactoring `_resolve_repo_path()` (signatures differ between CLI and server — CLI uses atexit cleanup, server returns temp_root for manual cleanup)
- Adding new tests beyond what's needed for the shared module
- Changing any runtime behavior

---

## TODO

### 1. Extract duplicate git helpers to `lib/git_utils.py`
- [x] Create `src/helping_hands/lib/git_utils.py` with `github_clone_url`, `git_noninteractive_env`, `redact_sensitive`, `repo_tmp_dir`
- [x] Add `__all__` with public exports
- [x] Add Google-style docstrings

### 2. Update consumers to use shared module
- [x] Update `cli/main.py` to import from `lib/git_utils`
- [x] Update `server/celery_app.py` to import from `lib/git_utils`
- [x] Update `lib/github.py` to import `redact_sensitive` from `lib/git_utils`
- [x] Remove duplicate function definitions from all three files

### 3. Replace bare `except Exception` in health checks
- [x] `_check_redis_health()` — catch `(ImportError, OSError, ValueError)` instead of `Exception`
- [x] `_check_db_health()` — catch `(ImportError, OSError)` instead of `Exception`
- [x] `_check_workers_health()` — catch `(OSError, AttributeError)` instead of `Exception`

### 4. Add MkDocs page and update mkdocs.yml
- [x] Create `docs/api/lib/git_utils.md` with mkdocstrings directive
- [x] Add to `mkdocs.yml` nav under lib
- [x] Update `docs/index.md` API reference links

### 5. Run verification
- [x] `uv run ruff check .` — lint clean
- [x] `uv run ruff format --check .` — format clean
- [x] `uv run pytest -v` — all 624 tests pass

### 6. Reconcile documentation surfaces
- [x] Update Obsidian Architecture.md MkDocs page count (37 → 38) and add git_utils layer
- [x] Update Obsidian AGENT.md page count (37 → 38) and module count (45 → 46)
- [x] Update Obsidian Concepts.md module count (45 → 46)
- [x] Update Obsidian Project todos.md page count (37 → 38)
- [x] Update root AGENT.md with recurring decisions and footer
- [x] Update W10 project log with session work

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created after codebase audit identified 4 duplicate helpers across 3 files and 3 bare except patterns |
| 2026-03-01 | Created `lib/git_utils.py` with 4 public functions, `__all__`, and Google-style docstrings |
| 2026-03-01 | Updated `cli/main.py`, `server/celery_app.py`, and `lib/github.py` to import from shared module; removed duplicate definitions |
| 2026-03-01 | Replaced 3 bare `except Exception` in `server/app.py` health checks with specific types |
| 2026-03-01 | Created MkDocs page for `git_utils`; updated `mkdocs.yml` nav and `docs/index.md` links |
| 2026-03-01 | Reconciled all 6 documentation surfaces: Architecture.md, Concepts.md, Obsidian AGENT.md, Project todos.md, root AGENT.md, W10 project log |
| 2026-03-01 | Verification: `ruff check` clean, `ruff format --check` clean, 624 tests passed. PRD completed. |
