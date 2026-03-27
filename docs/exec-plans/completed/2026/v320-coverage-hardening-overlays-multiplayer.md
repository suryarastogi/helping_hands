# v320 — Coverage Hardening: AppOverlays & useMultiplayer

## Goal

Push coverage for two files with uncovered branches:
- `AppOverlays.tsx`: 83.53% stmts → >95% (testNotification function, lines 83–110)
- `useMultiplayer.ts`: 80.76% branch → >83% (position/cursor throttle timer clearing, lines 505–507/702–704)

## Tasks

1. **AppOverlays testNotification tests** — Cover:
   - Notification API unavailable (falls back to `alert`)
   - Permission not yet granted (requests permission, recurses on grant)
   - Service worker registration present (calls `reg.showNotification`)
   - SW `showNotification` error path (calls `alert`)
   - Fallback `new Notification()` when no SW reg
   - Fallback `new Notification()` error path (calls `alert`)

2. **useMultiplayer throttle timer edge case** — Cover:
   - Position broadcast: when throttle interval has elapsed AND a pending timer exists, the timer is cleared before immediate broadcast
   - Cursor broadcast: same pattern for cursor throttle

3. **Docs** — Update INTENT.md, FRONTEND.md, daily consolidation

## Success criteria

- All existing 674 tests still pass
- New tests cover the identified gaps
- Overall branch coverage stays ≥90%
