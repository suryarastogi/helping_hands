# PRD: API Validation Hardening & Documentation Reconciliation

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Close the highest-impact validation gaps in the FastAPI request layer, improve health check observability, and reconcile all documentation surfaces (docs, docstrings, obsidian).

---

## Problem Statement

The helping_hands codebase has strong architecture and comprehensive test coverage (347+ tests), but an audit reveals concrete gaps across three areas:

1. **`BuildRequest` lacks input validation bounds.** The `repo_path` and `prompt` fields accept empty strings, `max_iterations` has no upper bound, and `pr_number` has no `ge=1` constraint. Invalid inputs pass Pydantic validation and only fail downstream in Celery workers, producing confusing errors.

2. **Health check endpoints swallow all exceptions.** The three `_check_*_health()` functions in `app.py` use bare `except Exception:` with no logging — making production debugging of Redis/Postgres/worker connectivity issues harder than necessary.

3. **`ScheduleRequest.cron_expression` has no syntax validation.** Invalid cron strings are accepted and stored, only failing at next execution time. The `croniter` dependency is already available.

4. **`Config.__post_init__` has no docstring.** This method runs validation on every Config creation but isn't documented, making the validation contract invisible to developers.

5. **Documentation surfaces need reconciliation.** The obsidian `AGENT.md` is a placeholder redirect instead of containing useful conventions for vault readers. The Project Log needs updating. The `Project todos.md` design notes need to reflect recent changes.

## Success Criteria

- [x] `BuildRequest` has validation bounds: `repo_path` min_length=1, `prompt` min_length=1, `max_iterations` ge=1 le=100, `pr_number` ge=1
- [x] `ScheduleRequest` has `repo_path` min_length=1, `prompt` min_length=1, `max_iterations` le=100
- [x] `ScheduleRequest.cron_expression` validates syntax using croniter
- [x] Health check functions log exceptions at warning level with context
- [x] `Config.__post_init__` has a Google-style docstring
- [x] Obsidian `AGENT.md` contains useful conventions for vault readers
- [x] Obsidian Project Log updated with this session's work
- [x] All tests pass (367 passed)

## Non-Goals

- Adding retry/backoff logic for transient health check failures
- Rewriting health check architecture
- Adding new API endpoints or features
- Changing hand behavior or code execution

---

## TODO

### 1. Add validation bounds to `BuildRequest`
- [x] `repo_path`: `Field(min_length=1)`
- [x] `prompt`: `Field(min_length=1)`
- [x] `max_iterations`: `Field(default=6, ge=1, le=100)`
- [x] `pr_number`: `Field(default=None, ge=1)`

### 2. Add validation bounds to `ScheduleRequest`
- [x] `repo_path`: `Field(min_length=1)`
- [x] `prompt`: `Field(min_length=1)`
- [x] `max_iterations`: `Field(default=6, ge=1, le=100)`

### 3. Add cron expression validation to `ScheduleRequest`
- [x] Add `field_validator` for `cron_expression` that checks syntax with `validate_cron_expression()` from `schedules.py`
- [x] Accepts both raw cron expressions and preset names (e.g., `hourly`, `daily`) via existing `CRON_PRESETS` lookup

### 4. Replace bare `except Exception:` in health checks with logged exceptions
- [x] `_check_redis_health()`: log warning with `exc_info=True`
- [x] `_check_db_health()`: log warning with `exc_info=True`
- [x] `_check_workers_health()`: log warning with `exc_info=True`
- [x] `_resolve_worker_capacity()`: log warning with `exc_info=True`

### 5. Add docstring to `Config.__post_init__`
- [x] Document that it validates `repo` format and warns on unexpected `model` patterns

### 6. Reconcile documentation surfaces
- [x] Populate obsidian `AGENT.md` with conventions summary for vault readers
- [x] Update Obsidian Project Log `2026-W09.md` with this session's work
- [x] Update `obsidian/docs/Project todos.md` design notes with latest changes

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created; codebase audit identified validation, observability, and documentation gaps |
| 2026-03-01 | Added `Field(min_length=1)` to `BuildRequest.repo_path`/`prompt`, `Field(ge=1, le=100)` to `max_iterations`, `Field(ge=1)` to `pr_number` |
| 2026-03-01 | Added `Field(min_length=1)` to `ScheduleRequest.repo_path`/`prompt`, `Field(le=100)` to `max_iterations`; added `_validate_cron` field validator using `validate_cron_expression()` |
| 2026-03-01 | Added `logging` import and `logger` to app.py; replaced bare `except Exception:` with `logger.warning(..., exc_info=True)` in 4 health/capacity functions |
| 2026-03-01 | Added Google-style docstring to `Config.__post_init__` |
| 2026-03-01 | Populated obsidian `AGENT.md` with code style, design principles, recurring decisions, and testing conventions |
| 2026-03-01 | Updated Project Log W09 and Project todos with this session's changes |
| 2026-03-01 | All 367 tests pass; lint and format clean. PRD moved to completed/ |
