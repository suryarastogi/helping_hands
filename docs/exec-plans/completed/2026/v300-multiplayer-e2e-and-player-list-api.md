# v300: Multiplayer E2E Tests & Player List API

**Status:** Completed

## Goal

Two self-contained improvements to multiplayer observability and test coverage:
1. **Player list REST endpoint** — Expose connected player details via `/health/multiplayer/players` so external tools can query who's online
2. **E2E multiplayer test** — Playwright multi-context test proving two browser windows see each other's avatars

## Tasks

- [x] Add `get_connected_players()` to `multiplayer_yjs.py`
- [x] Add `GET /health/multiplayer/players` endpoint to `app.py`
- [x] Add backend tests for player list endpoint
- [x] Add Playwright e2e test with two browser contexts for multiplayer
- [x] Update design doc and FRONTEND.md
- [x] Run full test suite — verify all pass

## Technical Approach

### Player list endpoint
- Parse Yjs awareness states from `WebsocketServer.rooms` to extract player metadata
- Return `{players: [{player_id, name, color, x, y, idle}], count: N}`
- Graceful fallback when pycrdt-websocket not installed

### E2E multiplayer test
- Use Playwright's `browser.newContext()` to create two isolated browser contexts
- Both navigate to the app; both should render their local player
- Since e2e tests mock API routes (no real backend), test focuses on verifying
  scene rendering and player avatar presence in each context
- Add a live-server variant that can test real Yjs synchronisation when backend available

## Test Plan
- Backend: player list returns empty when no connections, correct structure
- E2E: two contexts both show Hand World scene, player avatars visible
