# v278: Legacy WebSocket Cleanup & Connection Status UI

**Status:** Completed
**Created:** 2026-03-23
**Intent:** Remove dead legacy WebSocket endpoint, add Yjs connection status indicator

## Goal

Now that Yjs awareness (v276) is the primary multiplayer sync mechanism:
1. Remove the legacy `/ws/world` custom WebSocket endpoint and `multiplayer.py` module
2. Add a connection status indicator to the Hand World UI showing connected/reconnecting/disconnected state
3. Update tests to match the new state

## Analysis

The legacy `/ws/world` endpoint in `multiplayer.py` is no longer used by the frontend
(which connects exclusively to `/ws/yjs`). Keeping it adds maintenance burden and
confusion about which endpoint is authoritative. Meanwhile, the frontend has no
indication of Yjs connection health — it just says "Multiplayer active" with no
feedback when the connection drops.

## Tasks

### Phase 1: Remove legacy WebSocket endpoint
- [x] Remove `/ws/world` route from `app.py`
- [x] Remove `multiplayer.py` import from `app.py`
- [x] Delete `src/helping_hands/server/multiplayer.py`
- [x] Delete `tests/test_multiplayer.py` (tests the removed module)
- [x] Verify no other code references `multiplayer.py` or `/ws/world`

### Phase 2: Connection status indicator
- [x] Track Yjs provider status (`connecting`, `connected`, `disconnected`) in React state
- [x] Render connection status dot/badge in the multiplayer status panel
- [x] Style status indicator (green=connected, yellow=connecting, red=disconnected)

### Phase 3: Testing
- [x] Frontend unit test: connection status renders correctly for each state
- [x] Verify existing Yjs tests still pass

### Phase 4: Documentation
- [x] Update design doc to note legacy endpoint removal
- [x] Consolidate v276+v277 into daily/weekly summaries
- [x] Update PLANS.md index
- [x] Move plan to completed

## Dependencies
- v276 (Yjs multiplayer sync) — completed
- v277 (multiplayer test coverage) — completed
