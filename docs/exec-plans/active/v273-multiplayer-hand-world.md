# v273 — Multiplayer Hand World (yjs awareness)

**Created:** 2026-03-23
**Status:** Active

## Goal

Make the Hand World view multiplayer: multiple users see each other's avatars
moving in real time, synchronized through the Python backend using yjs.

## Tasks

- [x] Create INTENT.md with user's multiplayer intent
- [x] Create active execution plan
- [x] Consolidate 2026-03-16 and 2026-03-17 daily plans into Week-12 if needed
- [x] Add `pycrdt-websocket` to Python dependencies (server extra)
- [x] Add `yjs` + `y-websocket` to frontend dependencies
- [x] Implement WebSocket multiplayer endpoint in `src/helping_hands/server/multiplayer.py`
- [x] Mount WebSocket route in FastAPI app
- [x] Add frontend yjs awareness hook (`useMultiplayer`)
- [x] Render remote player avatars in Hand World scene
- [x] Add Python tests for multiplayer WebSocket endpoint (15 tests)
- [x] Add frontend unit tests for multiplayer hook (9 tests)
- [x] Update E2E tests for multiplayer presence
- [x] Update docs: FRONTEND.md, design-docs, ARCHITECTURE.md
- [ ] All existing tests pass (Python + frontend)
- [ ] Move plan to completed

## Completion criteria

- WebSocket endpoint `/ws/world` accepts connections and relays binary messages
- Frontend `useMultiplayer` hook connects to backend, broadcasts local player state
- Remote players rendered with distinct colors and name labels in Hand World scene
- Status summary shows multiplayer connection count
- 15 Python tests for `MultiplayerRoom` pass
- 9 frontend tests for `useMultiplayer` hook pass
- All existing tests (7357+ Python, 180+ frontend) continue to pass
- Design doc, FRONTEND.md, and ARCHITECTURE.md updated

## Architecture

```
Browser A ──ws──┐
                ├── FastAPI /ws/world ── MultiplayerRoom relay
Browser B ──ws──┘
```

Each client:
1. Creates a yjs `Doc` + `WebsocketProvider` pointing at `/ws/world`
2. Sets local awareness state: `{ position, direction, walking, color, name }`
3. Listens to awareness changes → renders remote player sprites

Backend:
- `MultiplayerRoom` class relays WebSocket messages to all peers
- No persistent state needed — awareness is ephemeral presence data
- Mounted via `mount_multiplayer(app)` on the FastAPI app
