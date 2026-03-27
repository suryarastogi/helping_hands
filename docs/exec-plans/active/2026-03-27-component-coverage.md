# Execution Plan: AppOverlays & MonitorCard Component Coverage

**Created:** 2026-03-27
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Raise AppOverlays.tsx from 83.53% to 90%+ and MonitorCard.tsx from 85.46% to 90%+ statement coverage with semantically meaningful tests.

## Context

Frontend was at 681 tests / 90.41% branch coverage. Two components sat below the 90% statement threshold:
- `AppOverlays.tsx` — lines 83–110 uncovered (testNotification function: Notification API unavailable alert, permission re-request flow, SW-based notification, fallback `new Notification`)
- `MonitorCard.tsx` — lines 153–165 uncovered (prefix filter cycling onClick: show→hide→only→show), lines 197–200 (task error banner), lines 33-34 (taskError prop)

## Tasks

- [x] **AppOverlays: testNotification when Notification API unavailable** — alert fallback
- [x] **AppOverlays: testNotification permission re-request flow** — requestPermission then recursive call
- [x] **AppOverlays: testNotification with SW registration** — showNotification via service worker reg
- [x] **AppOverlays: testNotification fallback new Notification** — when swReg is null
- [x] **AppOverlays: requestNotifPermission Enable button + rejection** — calls requestPermission, handles rejection
- [x] **MonitorCard: prefix filter cycling** — clicking chip cycles show→hide→only→show (3 tests)
- [x] **MonitorCard: task error banner** — renders errorType and error message + null guard
- [x] **MonitorCard: copy button** — clipboard.writeText call
- [x] **MonitorCard: prefix chip icons** — correct icon per mode (●/○/◉)
- [x] **MonitorCard: info badge tooltips** — task ID and null states
- [x] **MonitorCard: reset all filters** — clears all prefix filters
- [x] **Documentation updates** — PLANS.md, daily consolidation

## Completion criteria

- [x] AppOverlays.tsx statement coverage ≥ 90% — **achieved 100%**
- [x] MonitorCard.tsx statement coverage ≥ 90% — **achieved 96.51%**
- [x] All frontend tests pass with no regressions — **697 tests pass**

## Results

- **Frontend tests:** 681 → 697 (+16)
- **AppOverlays.tsx:** 83.53% → 100% statements, 97.43% → 98% branch
- **MonitorCard.tsx:** 85.46% → 96.51% statements, 90.24% → 98.14% branch
- **Overall branch coverage:** 90.41% → 90.72%
