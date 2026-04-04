# Adding Task Parameters

Checklist for adding a new user-facing parameter (checkbox, input, etc.) to
the task submission and scheduling system.

## Context

Task parameters flow through many layers: frontend form state, API request
models, Celery task signatures, progress reporting, hand execution, and
schedule persistence. Missing a single layer causes the value to silently
default to its zero value. This document enumerates every touch point so new
parameters are wired end-to-end.

Use `fix_ci` as a reference implementation — grep for it to see the exact
pattern at each layer.

## Checklist

### 1. Backend models — `server/app.py`

- [ ] `BuildRequest` — Pydantic model for `/build` JSON endpoint
- [ ] `ScheduleRequest` — Pydantic model for `/schedules` create/update
- [ ] `ScheduleResponse` — Pydantic response model returned to frontend

### 2. Schedule persistence — `server/schedules.py`

- [ ] `ScheduledTask` dataclass — field with default value
- [ ] `ScheduledTask.to_dict()` — include in serialization dict
- [ ] `ScheduledTask.from_dict()` — deserialize with `data.get()` fallback
- [ ] Docstring — add parameter description to the class docstring

### 3. Celery task — `server/celery_app.py`

- [ ] `build_feature()` task signature — add keyword argument with default
- [ ] `_ProgressEmitter.__init__()` — add parameter and store as `self._<name>`
- [ ] `_ProgressEmitter.emit()` — forward via `overrides.get("<name>", self._<name>)`
- [ ] `_update_progress()` signature — add keyword argument
- [ ] `_update_progress()` meta dict — include in the dict passed to `update_state`
- [ ] `_update_progress()` docstring — document the new parameter
- [ ] Hand setup block (~line 1206) — assign `hand.<name> = <name>`
- [ ] Result dict — include `str(<name>).lower()` in the final return dict
- [ ] `scheduled_build()` — pass `schedule.<name>` to `build_feature.delay()`

### 4. Schedule dispatch — `server/schedules.py` (dispatch paths)

There are **three** places that dispatch `build_feature`:

- [ ] `_launch_interval_chain()` — `build_feature.apply_async(kwargs={...})`
      *(interval schedules — easy to miss)*
- [ ] `trigger_schedule()` cron path — `build_feature.delay(...)`
- [ ] `scheduled_build()` in `celery_app.py` — RedBeat cron trigger
      *(listed in step 3 above)*

### 5. Hand base class — `lib/hands/v1/hand/base.py`

- [ ] `Hand.__init__()` — add `self.<name>: <type> = <default>` attribute

### 6. Hand execution — `lib/hands/v1/hand/cli/base.py` (if behavior needed)

- [ ] Add implementation methods (logic that uses the new parameter)
- [ ] Wire into `run()` and/or `stream()` methods
- [ ] Add any new metadata constants to `base.py` and import them

### 7. Server HTML/JS — `server/app.py` (embedded fallback UI)

The server has an embedded HTML/JS fallback UI. Update all of these:

- [ ] HTML form checkbox/input — main build form
- [ ] HTML form checkbox/input — schedule form
- [ ] `applyQueryDefaults()` JS — read URL param and set element
- [ ] Form submission JS — read element value into payload
- [ ] Schedule submission JS — read element value into payload
- [ ] Schedule edit population JS — set element from schedule data

### 8. Server endpoints — `server/app.py` (Python)

- [ ] `_enqueue_build_task()` — pass `req.<name>` to `build_feature.delay()`
- [ ] `_build_form_redirect_query()` — add parameter and query string entry
- [ ] `enqueue_build_form()` — add `Form()` parameter
- [ ] `enqueue_build_form()` validation error redirect — pass to `_build_form_redirect_query()`
- [ ] `enqueue_build_form()` `BuildRequest` construction — pass the value
- [ ] `enqueue_build_form()` success redirect query — add `if req.<name>` block
- [ ] `create_schedule()` — pass `request.<name>` to `ScheduledTask()`
- [ ] `update_schedule()` — pass `request.<name>` to `ScheduledTask()`
      *(easy to miss — separate from create)*
- [ ] `_schedule_to_response()` — pass `task.<name>` to `ScheduleResponse()`

### 9. Frontend types — `frontend/src/types.ts`

- [ ] `FormState` type
- [ ] `ScheduleItem` type
- [ ] `ScheduleFormState` type

### 10. Frontend defaults — `frontend/src/App.utils.ts`

- [ ] `INITIAL_FORM` default value
- [ ] `INITIAL_SCHEDULE_FORM` default value

### 11. Frontend components

- [ ] `SubmissionForm.tsx` — checkbox/input in the form
- [ ] `ScheduleCard.tsx` — checkbox/input in the schedule form

### 12. Frontend hooks

**`useTaskManager.ts`:**

- [ ] `submitBuild()` body dict (first occurrence — direct submit)
- [ ] `submitBuild()` body dict (second occurrence — merged/grill submit)
- [ ] Task detail items — `readBoolish()`/`readString()` + `items.push()`
- [ ] URL param initialization — `params.get()` + `parseBool()` into form state

**`useSchedules.ts`:**

- [ ] `editSchedule()` — map `item.<name>` to form state
- [ ] `saveSchedule()` — include in request body

### 13. Tests

- [ ] Any `_Stub` / `_FakeScheduledTask` classes that manually set attributes
- [ ] Any assertion dicts that enumerate all task parameters
- [ ] Search tests for `fix_ci` to find all patterns that need updating

## How to verify

After adding a new parameter, run this grep to confirm no layer was missed:

```bash
# Should appear in all key files:
grep -rn 'new_param_name' \
  src/helping_hands/server/app.py \
  src/helping_hands/server/celery_app.py \
  src/helping_hands/server/schedules.py \
  src/helping_hands/lib/hands/v1/hand/base.py \
  frontend/src/types.ts \
  frontend/src/App.utils.ts \
  frontend/src/components/SubmissionForm.tsx \
  frontend/src/components/ScheduleCard.tsx \
  frontend/src/hooks/useTaskManager.ts \
  frontend/src/hooks/useSchedules.ts
```

Then run the full test suite — missing fields in test stubs will cause
`AttributeError` failures that point to the exact location.

## Common mistakes

1. **Forgetting `update_schedule()`** — The create and update endpoints
   construct `ScheduledTask` independently. Adding to create but not update
   means edits silently reset the value.

2. **Forgetting `_launch_interval_chain()`** — Interval schedules dispatch
   via `apply_async(kwargs={...})` in `schedules.py`, separate from the
   cron dispatch in `celery_app.py`. Missing this means interval-scheduled
   tasks always get the default value.

3. **Forgetting test stubs** — Several test files define minimal `_Stub` or
   `_FakeScheduledTask` classes that bypass `__init__`. These need the new
   attribute or the `run()`/`stream()` methods will raise `AttributeError`.

## Alternatives considered

- **Single source of truth dict** — Defining parameter names once and
  generating models/forms from it would eliminate drift but adds
  metaprogramming complexity inappropriate for the current codebase size.

- **Pydantic model inheritance** — Sharing a base model between request,
  response, and task could reduce duplication but couples layers that should
  remain independent.

## Consequences

- Adding a parameter requires touching ~15 files across 4 layers. This is
  the cost of a multi-process architecture (frontend → API → Celery → hand)
  with both React and embedded HTML UIs.
- The grep verification step catches most omissions. The test suite catches
  the rest via `AttributeError` on missing stub attributes.
