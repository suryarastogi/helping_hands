# v295 — Extract ScheduleCard Component

**Status:** completed
**Created:** 2026-03-23

## Goal

Extract the inline schedule form and schedule list JSX (~335 lines) from `App.tsx`
into a dedicated `ScheduleCard` component, continuing the frontend decomposition
started in v280–v294.

## Motivation

App.tsx was 1,891 lines. The schedule card (form fields + schedule list + inline
edit) was the largest remaining inline JSX block (~335 lines). Extracting it follows
the same pattern as MonitorCard (v293) and SubmissionForm (v294).

## Tasks

- [x] Create `frontend/src/components/ScheduleCard.tsx` with `ScheduleCardProps` interface
- [x] Internal `ScheduleFormFields` sub-component for reuse in new/edit modes
- [x] Move schedule form fields and schedule list JSX from App.tsx
- [x] Remove unused `CRON_PRESETS` and `backendDisplayName` imports from App.tsx
- [x] Create `frontend/src/components/ScheduleCard.test.tsx` — 20 tests
- [x] All 398 frontend tests pass (up from 378)
- [x] Lint passes

## Result

- App.tsx: 1,891 → 1,575 lines (-316 lines)
- New file: `ScheduleCard.tsx` (274 lines) with `ScheduleCardProps` (16 props)
- New file: `ScheduleCard.test.tsx` — 20 tests covering rendering, callbacks, form states, error display
- 398 frontend tests total
