# v322 — Extract Throttled Broadcast Utility from useMultiplayer

**Date:** 2026-03-27
**Theme:** Code quality — reduce duplication in multiplayer hook

## Problem

`useMultiplayer.ts` (798 lines) contains two nearly identical throttle implementations:
1. **Position broadcast** (lines 493–541): leading+trailing throttle at 60ms
2. **Cursor broadcast** (lines 711–753): leading+trailing throttle at 100ms

Both follow the same pattern:
- Track `lastBroadcastRef` timestamp and `timerRef` for pending deferred call
- If elapsed >= interval, broadcast immediately (clearing any pending timer)
- Otherwise, schedule a trailing broadcast for the remaining interval
- Null cursor has a special "immediate + cancel pending" path

## Plan

### Step 1: Extract `createThrottledBroadcast` utility

Create `frontend/src/utils/throttledBroadcast.ts` with a factory function
that returns `{ fire, cancel }`:

```ts
type ThrottledBroadcast = {
  fire: (fn: () => void) => void;
  cancel: () => void;
};
function createThrottledBroadcast(intervalMs: number): ThrottledBroadcast;
```

### Step 2: Refactor useMultiplayer to use the utility

Replace the inline throttle logic in the position broadcast effect and the
`updateCursor` callback with `createThrottledBroadcast` instances.

### Step 3: Add unit tests for createThrottledBroadcast

- Immediate fire when interval has elapsed
- Trailing fire when within interval
- Cancel clears pending timer
- Multiple rapid fires only produce one trailing call

### Step 4: Verify existing tests pass

All 691 frontend tests must continue to pass after refactoring.

## Success criteria

- `useMultiplayer.ts` reduced by ~30 lines
- New utility is independently testable
- All existing tests green
- No behavior change (throttle semantics identical)
