# v316 — Cursor Broadcast Throttle Coverage

**Status:** Completed
**Date:** 2026-03-27

## Goal

Close the remaining branch coverage gap in the `useMultiplayer` hook's cursor
broadcast throttle logic. The position broadcast throttle has dedicated tests
(v313), but the cursor throttle's leading+trailing pattern is only exercised by
basic broadcast/null tests. Three branches are untested:

1. Immediate cursor broadcast when `CURSOR_BROADCAST_INTERVAL_MS` has elapsed
2. Throttled cursor updates within the interval (trailing broadcast deferred)
3. `updateCursor(null)` cancelling a pending throttle timer

## Tasks

- [x] Add test: cursor throttle — immediate broadcast when window elapsed
- [x] Add test: cursor throttle — rapid updates within window are throttled
- [x] Add test: cursor null cancels pending throttle timer
- [x] Update docs (INTENT.md, design doc, daily consolidation)

## Approach

- Mirror the existing position throttle test pattern from v313
- Use `vi.useFakeTimers()` to control timing
- Test the three cursor throttle branches in `updateCursor()`
- No code changes needed — this is coverage-only
