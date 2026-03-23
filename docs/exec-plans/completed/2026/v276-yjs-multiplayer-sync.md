# v276: Yjs-Based Multiplayer Synchronisation

**Status:** Completed
**Created:** 2026-03-23
**Intent:** Migrate Hand World multiplayer sync from custom WebSocket protocol to Yjs awareness

## Goal

Replace the bespoke JSON-over-WebSocket multiplayer protocol with Yjs, using the
awareness layer for ephemeral player presence (position, direction, walking state,
emotes). This aligns with the user's preference for Yjs-powered frontends and
provides built-in offline/reconnect handling, automatic peer cleanup, and a
well-tested CRDT synchronisation protocol.

## Architecture

```
Frontend (React)               Backend (FastAPI)
─────────────────              ─────────────────
Y.Doc + Awareness  ◄──ws──►   pycrdt-websocket
                                ASGIServer mounted
                                at /ws/yjs/{room}
```

- **Frontend:** `yjs` + `y-websocket` WebsocketProvider connected to room `hand-world`
- **Backend:** `pycrdt-websocket` ASGIServer mounted on `/ws/yjs`
- **Awareness state per client:** `{ name, color, x, y, direction, walking, emote }`
- **Color/name assignment:** Derived client-side from `Y.Doc.clientID`

## Tasks

### Phase 1: Dependencies
- [ ] Add `pycrdt>=0.12` and `pycrdt-websocket>=0.15` to `[server]` optional deps
- [ ] Add `yjs` and `y-websocket` to `frontend/package.json`

### Phase 2: Backend — Yjs WebSocket Relay
- [ ] Create `src/helping_hands/server/multiplayer_yjs.py`
  - WebsocketServer lifecycle (start/stop)
  - ASGIServer wrapper
  - Graceful fallback if pycrdt-websocket not installed
- [ ] Mount ASGIServer at `/ws/yjs` in `app.py`
- [ ] Keep existing `/ws/world` endpoint for backward compatibility

### Phase 3: Frontend — Yjs Awareness Migration
- [ ] Add `useYjsMultiplayer` hook logic in App.tsx
  - Create Y.Doc + WebsocketProvider on world view enter
  - Set local awareness state (position, direction, walking, emote)
  - Map remote awareness states to `remotePlayers` array
  - Clean up on view exit
- [ ] Wire emote key bindings to awareness state updates
- [ ] Remove old custom WebSocket multiplayer code

### Phase 4: Testing
- [ ] Backend: test Yjs relay module creation and lifecycle
- [ ] Frontend: test awareness state setting and remote player mapping

### Phase 5: Documentation
- [ ] Update FRONTEND.md with Yjs architecture
- [ ] Update INTENT.md
- [ ] Update multiplayer design doc

## Awareness Protocol

```
Each client sets local awareness state:
  { name: "Player 42", color: "#e11d48", x: 50, y: 50,
    direction: "down", walking: false, emote: null }

All clients receive awareness changes automatically.
Disconnected clients are cleaned up by Yjs after timeout (~30s).
```

## Dependencies
- `pycrdt>=0.12` (Python, server extra)
- `pycrdt-websocket>=0.15` (Python, server extra)
- `yjs` (npm)
- `y-websocket` (npm)
