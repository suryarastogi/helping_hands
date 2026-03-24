# v301 — Player Interaction Tooltips & Reconnection Banner

**Status:** Completed
**Date:** 2026-03-24

## Goal

Improve multiplayer UX with two self-contained features:
1. **Player interaction tooltips** — hover over a remote player avatar to see
   their name, status (active/idle/typing/walking), and color indicator.
2. **Reconnection overlay banner** — when the WebSocket connection drops, show a
   translucent "Reconnecting…" banner over the scene with a spinner animation.

## Tasks

- [x] Add tooltip state + rendering to `PlayerAvatar` (show on hover for remote players)
- [x] Add `.player-tooltip` CSS styles (positioned above avatar, with arrow)
- [x] Add reconnection banner to `HandWorldScene` (shown when `connectionStatus === "connecting"`)
- [x] Add `.reconnect-banner` CSS styles (translucent overlay with spinner animation)
- [x] Add tests: PlayerAvatar tooltip (7 tests — hover show/hide, no local tooltip, status variants, color)
- [x] Add tests: HandWorldScene reconnection banner (3 tests — visible connecting, hidden connected/disconnected)
- [x] Update design doc with v301 section
- [x] Update FRONTEND.md

## Results

- 10 new tests (459 frontend tests total, up from 449)
- Lint, typecheck, and all tests pass
- Design doc updated with v301 tooltip and reconnection sections
- FRONTEND.md updated with new feature descriptions
