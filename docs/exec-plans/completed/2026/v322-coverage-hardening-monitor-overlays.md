# v322 — Coverage Hardening: MonitorCard, AppOverlays, useMultiplayer

**Date:** 2026-03-27
**Theme:** Test coverage hardening for uncovered branches

## Context

The multiplayer Hand World feature is complete (v273–v321). Frontend coverage
stands at 96.03% statements / 90.19% branches / 691 tests. This plan targets
the remaining uncovered branches in three files to push branch coverage above
91%.

## Tasks

1. **MonitorCard** (85.46% stmts → target ≥95%)
   - Cover prefix filter chip cycling (show → hide → only → show)
   - Cover `taskError` error banner rendering
   - Cover cancel button `onClick` callback

2. **AppOverlays** (83.53% stmts → target ≥95%)
   - Cover `testNotification` callback branches:
     - Notification API unavailable (alert fallback)
     - Permission not granted → request → re-invoke
     - Permission granted with service worker registration
     - Permission granted without service worker (fallback `new Notification`)

3. **useMultiplayer** (81.12% branch → target ≥84%)
   - Cover position throttle timer-clearing when broadcasting immediately (lines 522–525)
   - Cover cursor throttle timer-clearing when broadcasting immediately (lines 740–743)

## Expected Outcome

- ~12–15 new tests
- Overall branch coverage: 90.19% → ~91%+
- No new production code changes required
