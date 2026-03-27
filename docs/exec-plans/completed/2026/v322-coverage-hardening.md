# v322 — Frontend Coverage Hardening

**Date:** 2026-03-27
**Status:** Completed
**Branch:** helping-hands/claudecodecli-9f34267c

## Goal

Raise frontend coverage by targeting specific uncovered code paths in
AppOverlays.tsx, MonitorCard.tsx, and useMultiplayer.ts.

## Completed Tasks

| # | Task | File | Tests Added |
|---|------|------|-------------|
| 1 | Test `testNotification()` branches — API unavailable alert, permission request, SW showNotification, fallback `new Notification`, constructor throw | AppOverlays.tsx | 6 |
| 2 | Test prefix filter cycling (`show→hide→only→show`), reset button, chip icons, task error banner | MonitorCard.tsx | 7 |
| 3 | Test name/color broadcast no-op when value unchanged | useMultiplayer.ts | 2 |
| 4 | Document unreachable throttle timer guards and fallback branches in tech-debt-tracker | tech-debt-tracker.md | — |

## Results

| Metric | Before | After |
|--------|--------|-------|
| AppOverlays.tsx statements | 83.53% | **100%** |
| MonitorCard.tsx branch | 90.24% | **98.11%** |
| Overall frontend statements | 96.01% | **96.95%** |
| Overall frontend branch | 90.19% | **90.50%** |
| Frontend tests total | 691 | **706** |

## Notes

- useMultiplayer.ts lines 522–525 (position throttle guard) and 740–743 (cursor
  throttle guard) are unreachable because React's effect cleanup clears the timer
  ref before the next effect runs. Documented in tech-debt-tracker.
- useMultiplayer.ts lines 466 and 485 are fallback ternary branches for null
  `yjsDocRef.current`; unreachable because effects only fire when `active` is true
  and doc ref is set. Also documented in tech-debt-tracker.
