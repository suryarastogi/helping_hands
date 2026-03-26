# v310 — Fix Flaky WASD Test & Extract useSceneWorkers Hook

**Created:** 2026-03-26
**Status:** Completed

## Goals

1. Fix the flaky `moves player with WASD keys` test in `useMovement.test.tsx`
2. Extract `useSceneWorkers` hook from App.tsx (~100 lines of scene worker state management)
3. Update documentation and verify all tests pass

## Tasks

### 1. Fix flaky WASD movement test
- **Root cause:** The `requestAnimationFrame` mock always returns ID `1` across tests, causing timer interference between test cases. When the ArrowUp test's `movePlayer` chains a second rAF via `requestAnimationFrame(movePlayer)`, the resulting setTimeout may leak into subsequent tests.
- **Fix:** Use an incrementing counter for rAF mock IDs and add proper timer cleanup between tests via `beforeEach`/`afterEach`.

### 2. Extract useSceneWorkers hook
- **What:** Scene worker lifecycle management — spawning at factory, walking to desk, active phase, walking to exit, cleanup
- **Lines:** App.tsx ~595-699 (scene worker effects + claimSlotForTask + related state)
- **Interface:** Takes `activeTasks`, `maxOfficeWorkers`, `deskSlots`; returns `sceneWorkers`, `sceneWorkerEntries`

### 3. Add tests for useSceneWorkers
- Unit tests for the extracted hook covering worker lifecycle phases

### 4. Update docs
- INTENT.md: mark v310 as completed
- FRONTEND.md: update component listing
- Design docs: update as needed

## Acceptance Criteria
- All 536 tests pass (0 flaky)
- App.tsx reduced by ~100 lines
- No functional regressions
