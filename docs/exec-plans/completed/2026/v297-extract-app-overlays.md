# v297: Extract AppOverlays Component

**Date:** 2026-03-23
**Status:** Completed

## Goal

Extract the overlay UI elements (service health bar, toast notifications, notification permission banner) from App.tsx into a dedicated `AppOverlays` component.

## Motivation

App.tsx is 1,506 lines. The overlay elements at the bottom of the render are self-contained UI that don't interact with the main content flow. Extracting them continues the frontend decomposition effort.

## Tasks

- [x] Create `AppOverlays` component with props interface
- [x] Move serviceHealthIndicators, testNotification, serviceHealthBar, toast rendering, notification banner
- [x] Update App.tsx to use `<AppOverlays />`
- [x] Write tests for AppOverlays
- [x] Update FRONTEND.md component listing
- [x] Update INTENT.md
- [x] Verify lint, typecheck, all tests pass

## Scope

- ~60 lines of JSX + ~50 lines of supporting logic extracted from App.tsx
- New file: `frontend/src/components/AppOverlays.tsx`
- New file: `frontend/src/components/AppOverlays.test.tsx`
