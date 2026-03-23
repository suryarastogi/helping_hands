# v282 — Extract App types and utility functions

**Created:** 2026-03-23
**Status:** Active

## Goal

Move all remaining types from `App.tsx` into `types.ts` and extract ~650
lines of pure utility functions into a new `App.utils.ts` module. This
continues the decomposition of the 3,590-line monolith.

## Motivation

- `App.tsx` has ~170 lines of type definitions (lines 30-200) and ~650 lines
  of pure utility/helper functions (lines 381-1027) before the component
  starts at line 1029.
- Types belong in `types.ts`; utilities belong in a dedicated module.
- Tests already exist in `App.utils.test.ts` — they currently import from
  `./App` and will be updated to import from `./App.utils`.

## Tasks

- [x] **Move app types to `types.ts`** — 25 types moved: `Backend`,
  `BuildResponse`, `TaskStatus`, `CurrentTask`, `CurrentTasksResponse`,
  `WorkerCapacityResponse`, `FormState`, `TaskHistoryItem`, `TaskHistoryPatch`,
  `ServerConfig`, `ServiceHealth`, `ServiceHealthState`, `ScheduleItem`,
  `ScheduleFormState`, `ClaudeUsageLevel`, `ClaudeUsageResponse`, `OutputTab`,
  `PrefixFilterMode`, `MainView`, `DashboardView`, `SceneWorker`,
  `PlayerPosition`, `InputItem`, `DeskSlot`, `AccumulatedUsage`.
- [x] **Create `App.utils.ts`** (851 lines) — moved 30 pure functions and
  15 constants/config values. Includes fetch helpers, scene geometry,
  log parsing, task history, and provider mapping.
- [x] **Update `App.tsx`** — imports types from `types.ts` and functions/
  constants from `App.utils.ts`. Re-exports for backward compatibility so
  existing `import { ... } from "./App"` in tests still work.
- [x] **Update `App.utils.test.ts`** — imports constants from `./constants`
  and utilities from `./App.utils` (no longer depends on `./App`).
- [x] **Update `WorkerSprite.tsx`** — imports from `../App.utils` instead
  of `../App`.
- [x] **Update docs** — `PLANS.md`, `FRONTEND.md`, `INTENT.md`.

## Completion criteria

- `npm --prefix frontend run lint` passes
- `npm --prefix frontend run typecheck` passes
- `npm --prefix frontend run test` passes with ≥245 tests (245 passed)
- No type definitions remain in `App.tsx` (except inline generics)
- No pure utility functions remain in `App.tsx`
- App.tsx reduced from 3,590 to 2,691 lines (-899)
