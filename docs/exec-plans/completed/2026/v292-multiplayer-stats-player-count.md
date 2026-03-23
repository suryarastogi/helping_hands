# v292: Multiplayer Stats Endpoint & Player Count Badge

**Date:** 2026-03-23
**Status:** Completed
**Theme:** Multiplayer observability & UX polish

## Goal

Add a backend `/health/multiplayer` API endpoint reporting Yjs room stats (connected
clients, rooms) and surface a live player-count badge in the Hand World header. This
provides operational observability for the multiplayer system and makes the multi-user
presence more visible to players.

## Tasks

- [x] Create execution plan
- [ ] Backend: Add `get_multiplayer_stats()` to `multiplayer_yjs.py`
- [ ] Backend: Add `GET /health/multiplayer` endpoint in `app.py`
- [ ] Frontend: Add player count badge next to "Hand World" header
- [ ] Backend tests: `test_multiplayer_yjs.py` — stats with/without pycrdt
- [ ] Frontend tests: HandWorldScene player count badge rendering
- [ ] Update INTENT.md, FRONTEND.md, consolidate exec plan

## Technical Design

### Backend

`multiplayer_yjs.py` gains a `get_multiplayer_stats() -> dict` function that queries
the `WebsocketServer` for connected rooms and client counts. Returns a dict like:

```json
{
  "available": true,
  "rooms": 1,
  "connections": 3
}
```

When pycrdt is not installed, returns `{"available": false, "rooms": 0, "connections": 0}`.

`app.py` mounts `GET /health/multiplayer` calling this function.

### Frontend

The `HandWorldScene` header gains an inline player-count badge showing
`N players` (1 + remotePlayers.length) when multiplayer is connected.

## Risks

- The `WebsocketServer` API for querying rooms/connections may differ across
  pycrdt-websocket versions — use defensive access with fallbacks.
