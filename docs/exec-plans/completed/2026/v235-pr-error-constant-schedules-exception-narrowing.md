# v235 — `_META_PR_ERROR` constant, schedules.py exception narrowing

**Created:** 2026-03-16
**Status:** Completed

## Goal

Two self-contained improvements:

1. **Extract `_META_PR_ERROR` constant** — `"pr_error"` is used as a bare string 5 times
   across `base.py` (4×) and `cli/base.py` (1×). Add a named constant alongside the
   existing `_META_*` family and replace all bare usages.
2. **Narrow `except Exception` in `schedules.py`** — three Redis-operation handlers
   (`_save_meta`, `_delete_meta`, `_list_meta_keys`) catch bare `Exception`. Narrow to
   `(redis.RedisError, OSError)` for specificity.

## Tasks

- [x] Create this plan
- [x] Add `_META_PR_ERROR` constant to `base.py`
- [x] Replace bare `"pr_error"` strings in `base.py` (4 occurrences)
- [x] Import and use `_META_PR_ERROR` in `cli/base.py`
- [x] Narrow `except Exception` in `schedules.py` (3 handlers)
- [x] Add tests (15 new: all passed)
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All changes have tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/lib/hands/v1/hand/base.py` — new `_META_PR_ERROR` constant, 4× bare string replaced
- `src/helping_hands/lib/hands/v1/hand/cli/base.py` — import `_META_PR_ERROR`, 1× bare string replaced
- `src/helping_hands/server/schedules.py` — narrow 3 `except Exception` → `except (redis.RedisError, OSError)`
- `tests/test_v235_pr_error_constant_schedules_exception_narrowing.py` — 15 new AST + runtime tests
