# v273: Multiplayer Hand World

**Status:** Completed
**Created:** 2026-03-23
**Completed:** 2026-03-23
**Intent:** Make Hand World a multiplayer view with real-time avatar synchronization

## Goal

Enable multiple users to see each other walking around Hand World in real-time. Each user gets a unique colored avatar, and position updates are broadcast through the Python backend via WebSocket.

## Plan

### Phase 1: Backend WebSocket Endpoint
- [ ] Add `/ws/world` WebSocket endpoint to `server/app.py`
- [ ] Implement connection manager with join/leave/position broadcast
- [ ] Each client gets a unique player ID and random color on connect
- [ ] Server broadcasts position updates to all other connected clients

### Phase 2: Frontend WebSocket Client
- [ ] Add WebSocket connection logic when world view is active
- [ ] Send local player position updates on movement
- [ ] Receive and render remote player avatars
- [ ] Handle connect/disconnect/reconnect gracefully

### Phase 3: Remote Player Rendering
- [ ] Add `RemotePlayer` type and state management
- [ ] Render remote players with distinct colors and name tags
- [ ] Show player count in Factory Floor status panel
- [ ] CSS styles for remote player avatars

### Phase 4: Testing
- [ ] Backend: WebSocket endpoint unit tests (connect, broadcast, disconnect)
- [ ] Frontend: Vitest unit tests for multiplayer state management
- [ ] Update E2E test helpers if needed

### Phase 5: Documentation
- [ ] Update FRONTEND.md with multiplayer architecture
- [ ] Add design doc for multiplayer sync protocol

## Protocol Design

```
Client → Server (JSON):
  { "type": "position", "x": 50.0, "y": 50.0, "direction": "down", "walking": false }

Server → Client (JSON):
  { "type": "player_joined", "player_id": "abc123", "color": "#e11d48", "name": "Player 3", "x": 50, "y": 50 }
  { "type": "player_left", "player_id": "abc123" }
  { "type": "player_moved", "player_id": "abc123", "x": 55.0, "y": 45.0, "direction": "left", "walking": true }
  { "type": "players_sync", "players": [...] }  // full state on connect
```

## Dependencies
- No new Python packages (FastAPI has built-in WebSocket support)
- No new frontend packages (browser native WebSocket API)
