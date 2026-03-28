# v311: Extract useSceneWorkers Hook

**Status:** Completed
**Date:** 2026-03-26
**Theme:** Frontend code quality — continued App.tsx decomposition

## Summary

Extracted scene worker lifecycle management from App.tsx into a dedicated
`useSceneWorkers` hook, continuing the decomposition series.

## Tasks

- [x] Create `frontend/src/hooks/useSceneWorkers.ts` with worker lifecycle logic
- [x] Update App.tsx to consume the hook
- [x] Add tests in `useSceneWorkers.test.tsx`
- [x] Remove dead re-exports and consolidate types

## Changes

- New `frontend/src/hooks/useSceneWorkers.ts` (~210 lines)
  - `sceneWorkers` state, `maxOfficeWorkers` state, `slotByTaskRef` ref
  - `deskSlots` memo, `claimSlotForTask` callback
  - `sceneWorkerEntries` memo (enriched workers with task/desk/style/schedule)
  - `officeDeskRows` memo, `worldSceneStyle` memo
  - Capacity scaling effect, worker lifecycle effect, phase timer effect
- App.tsx reduced from 538 to 313 lines (-225 lines, -42%)
- Removed 48 lines of dead re-exports (no consumers)
- `SceneWorkerEntry` type consolidated in hook; `HandWorldScene` re-exports it

## Tests

- 16 new tests in `useSceneWorkers.test.tsx`
  - Default state, worker creation, slot assignment, capacity scaling
  - Provider style enrichment (goose vs claude), schedule annotation
  - Phase transitions (at-factory → walking-to-exit), re-activation
  - World scene style computation, desk position data, timer lifecycle
- 569 total frontend tests (up from 553)
