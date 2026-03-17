# v253: Simplify schedule getattr() to direct attribute access

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

`celery_app.py` `scheduled_build()` (lines 929–933) and `app.py`
`_schedule_to_response()` (lines 3907–3913) used defensive
`getattr(schedule, "field", default)` for fields that are defined on the
`ScheduledTask` dataclass with defaults. Since these fields always exist on
the dataclass, `getattr()` was unnecessarily defensive — the same pattern
fixed in v246 for `Config`.

Additionally, `app.py` line 3889 used `getattr(task, "schedule_id", "?")`
inside the error handler, but `schedule_id` is a required field on
`ScheduledTask`.

## Tasks

- [x] Replace 4× `getattr(schedule, ...)` in `celery_app.py` `scheduled_build`
      with direct `schedule.field` access
- [x] Replace 6× `getattr(task, ...)` in `app.py` `_schedule_to_response` with
      direct `task.field` access
- [x] Add AST-based tests confirming no `getattr` remains in target functions
- [x] Add tests verifying ScheduledTask field defaults and explicit values
- [x] Verify all existing tests pass

## Completion criteria

- No `getattr()` calls remain in `scheduled_build()` or `_schedule_to_response()`
- All existing tests pass
- New tests verify attribute access correctness
