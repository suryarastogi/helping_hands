# v251: _GITHUB_ERRORS constant + Celery inspect exception narrowing

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

1. The exception tuple `(GithubException, OSError)` is repeated 5 times across
   `base.py` (4×) and `e2e.py` (1×) with no shared constant.
2. Two `except Exception` blocks in `app.py` (`_safe_inspect_call` and
   `_collect_celery_current_tasks`) are overly broad — Celery inspect failures
   produce `(AttributeError, ConnectionError, OSError, TimeoutError)`.

## Tasks

- [x] Add `_GITHUB_ERRORS` constant to `base.py` (tuple of exception types)
- [x] Replace all 4 `except (GithubException, OSError)` in `base.py` with `except _GITHUB_ERRORS`
- [x] Import and use `_GITHUB_ERRORS` in `e2e.py` (1 occurrence)
- [x] Narrow `except Exception` in `app.py:3195` to `(AttributeError, ConnectionError, OSError, TimeoutError)`
- [x] Narrow `except Exception` in `app.py:3208` to `(AttributeError, ConnectionError, OSError, TimeoutError)`
- [x] Add tests for `_GITHUB_ERRORS` constant and narrowed exception handling
- [x] Update ARCHITECTURE.md and PLANS.md

## Completion criteria

- `_GITHUB_ERRORS` is the single source of truth for GitHub-related exception types
- No `except Exception` remains in app.py Celery inspect code
- All existing tests pass + new tests added
