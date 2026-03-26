# v310: Extract useTaskManager Hook

**Goal:** Extract task polling, submission, and history management from App.tsx
into a dedicated `useTaskManager` hook, continuing the App.tsx decomposition
series (v280–v309).

## Motivation

App.tsx is 1,374 lines. The largest remaining logic block (~400 lines) handles:
- Task polling (primary + background tasks)
- Task history persistence (localStorage)
- Task submission (`/build` POST)
- Task selection & view switching
- Floating numbers (update count deltas)
- Toast notifications & browser notifications
- Worker capacity polling
- Current tasks discovery

This is self-contained state that doesn't depend on the multiplayer or schedule
subsystems (those are already extracted).

## Plan

1. Create `frontend/src/hooks/useTaskManager.ts`
   - Move all task-related state: `taskId`, `status`, `payload`, `updates`,
     `isPolling`, `taskHistory`, `floatingNumbers`, `toasts`
   - Move polling effects: primary poll, background tracked-tasks poll,
     current-tasks discovery, worker capacity
   - Move callbacks: `submitRun`, `selectTask`, `openSubmissionView`
   - Move derived state: `selectedTask`, `activeTasks`, `activeTaskIds`,
     `taskById`, `accUsage`, `activeOutputText`, `taskInputs`
   - Move toast/notification helpers

2. Create `frontend/src/hooks/useTaskManager.test.tsx`
   - Test task submission (success, validation error, network error)
   - Test task selection switches to monitor view
   - Test polling starts on submission and stops on terminal status
   - Test toast creation on terminal status
   - Test floating number spawning on update count delta
   - Test task history localStorage persistence
   - Test current tasks discovery upserting

3. Update App.tsx to consume the hook
   - Replace ~400 lines of inline logic with hook call
   - Thread returned values to existing component props

4. Run full test suite to verify no regressions

## Acceptance criteria

- App.tsx reduced by ~350+ lines
- All existing 535+ frontend tests pass
- 10+ new tests for useTaskManager hook
- No behaviour changes in task polling, submission, or history
