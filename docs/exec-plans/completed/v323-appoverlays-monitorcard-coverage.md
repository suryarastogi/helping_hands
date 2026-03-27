# Execution Plan: AppOverlays & MonitorCard Branch Coverage

**Created:** 2026-03-27
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Cover uncovered branches in AppOverlays.tsx (testNotification function) and MonitorCard.tsx (prefix filter cycling, task error banner, cancel button), raising both components above 95% statement coverage.

## Context

Overall frontend branch coverage is 90.14%. Two components have notable gaps:
- `AppOverlays.tsx`: 83.53% stmts (lines 83–110 — `testNotification()` branches)
- `MonitorCard.tsx`: 85.46% stmts (lines 153–165 — prefix filter cycling, lines 197–200 — task error banner)

## Tasks

- [x] **AppOverlays testNotification tests** — 6 new tests: Notification API unavailable (alert), permission not granted (requests permission), permission granted without SW reg (new Notification), Notification constructor throws (alert), requestPermission rejection (graceful), requestPermission Enable button
- [x] **MonitorCard prefix filter cycling tests** — 3 new tests: show→hide, hide→only, only→show (removes key), plus 1 Reset button test
- [x] **MonitorCard task error banner tests** — 2 new tests: banner renders with error, banner absent when null
- [x] **MonitorCard cancel button tests** — 3 new tests: confirm + fetch, decline → no fetch, fetch error swallowed
- [x] **MonitorCard copy + prefix icon tests** — 4 new tests: copy to clipboard, prefix chip icons for show/hide/only modes
- [x] **Documentation updates** — Updated daily consolidation, weekly consolidation, INTENT.md

## Completion criteria

- AppOverlays.tsx statement coverage: 83.53% → 98.17% ✓
- MonitorCard.tsx statement coverage: 85.46% → 100% ✓
- All 717 frontend tests pass ✓
- Docs updated ✓

## Results

- **Frontend tests:** 698 → 717 (+19)
- **Overall statement coverage:** 96.02% → 97.06%
- **Overall branch coverage:** 90.14% → 90.47%
- **Component statement coverage:** 96.45% → 99.08%
