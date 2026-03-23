# v293: Extract MonitorCard Component

**Status:** Completed
**Created:** 2026-03-23
**Completed:** 2026-03-23
**Theme:** Frontend code quality — component extraction

## Goal

Extract the inline `monitorCard` JSX block from `App.tsx` into a dedicated
`MonitorCard` component. Continues the component extraction trajectory
(v280–v286) that reduced App.tsx from 3,590 to 2,189 lines.

## Changes

### New files
- `frontend/src/components/MonitorCard.tsx` — Task output monitor card with
  output tabs (Updates/Raw/Payload), prefix filter chips, accumulated API usage
  display, cancel button, resizable output pane, and task inputs details.
  `MonitorCardProps` interface with 17 typed props. Blinker color and animation
  computed internally from `status` prop.
- `frontend/src/components/MonitorCard.test.tsx` — 19 tests: idle rendering,
  task ID display, tab rendering/selection/callbacks, cancel button
  visibility (running vs terminal), output text, runtime display, prefix filter
  chips, payload tab filter hiding, accumulated usage, task inputs,
  empty inputs message, pulsing vs static blinker, custom height, reset button.

### Modified files
- `App.tsx` — Replaced ~146 lines of inline `monitorCard` JSX with
  `<MonitorCard />` component. Removed unused `statusBlinkerColor` import.
  Renamed `isBlinkerAnimated` to `isTaskRunning` (scoped to elapsed timer
  effect). Lines: 2,189 → 2,043 (-146).
- `docs/FRONTEND.md` — Added MonitorCard to component tree.
- `INTENT.md` — Added v293 completion entry.

## Acceptance Criteria

- [x] `MonitorCard.tsx` renders identically to the inline block
- [x] App.tsx reduced by 146 lines
- [x] 19 new component tests for rendering, tabs, prefix filters, cancel button
- [x] All 361 frontend tests pass (up from 342)
- [x] Lint and typecheck clean
