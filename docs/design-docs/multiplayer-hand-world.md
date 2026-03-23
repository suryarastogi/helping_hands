# Design Doc: Multiplayer Hand World

**Status:** Implemented (v273)
**Date:** 2026-03-23

## Context

The Hand World view is an isometric factory-themed visualization of AI worker
agents in the helping_hands frontend.  Users can walk around the scene with
arrow keys/WASD, watch worker bots activate at desks, and monitor task status.
The view was single-player — each browser tab had its own isolated player avatar.

## Problem

The Hand World view is single-player — each browser tab has its own isolated
player avatar with no awareness of other users.  Users want to see other
people walking around the same scene in real time.

## Solution

Use the **yjs awareness protocol** to synchronize lightweight presence data
(position, direction, walking state, color, name) between connected clients.
The backend acts as a simple WebSocket relay.

### Why yjs awareness (not full CRDT sync)?

- Player positions are ephemeral — no persistence needed
- Awareness protocol is built for exactly this use case (cursors, presence)
- Much lighter than full document sync (~50 bytes per awareness update)
- yjs ecosystem is well-maintained and widely used in collaborative editors

### Why a relay server (not peer-to-peer)?

- Works through NATs/firewalls without STUN/TURN configuration
- Consistent with the existing backend-centric architecture
- Easy to add server-side logic later (rate limiting, validation, analytics)

## Architecture

```
┌──────────────┐     ┌──────────────┐
│  Browser A   │     │  Browser B   │
│              │     │              │
│ yjs Doc      │     │ yjs Doc      │
│ Awareness ◄──┼─ws──┼──► Awareness │
│              │     │              │
│ Local player │     │ Local player │
│ Remote []    │     │ Remote []    │
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                │ WebSocket
       ┌────────▼─────────┐
       │  FastAPI Server   │
       │                   │
       │  /ws/world        │
       │  MultiplayerRoom  │
       │  (broadcast relay)│
       └───────────────────┘
```

### Data flow

1. Client connects to `/ws/world` via WebSocket
2. yjs `WebsocketProvider` handles the awareness protocol automatically
3. When local player moves → `awareness.setLocalStateField("player", {...})`
4. yjs encodes this as an awareness update message and sends it over WebSocket
5. Server receives binary message, broadcasts to all other connected clients
6. Remote clients decode the awareness update and render the remote player

### Awareness state shape

```typescript
{
  player: {
    position: { x: number; y: number },  // percentage-based
    direction: "up" | "down" | "left" | "right",
    walking: boolean,
    name: string,    // randomly assigned per tab
    color: string,   // randomly assigned per tab
  }
}
```

## Files changed

| File | Change |
|---|---|
| `src/helping_hands/server/multiplayer.py` | New: WebSocket relay room + mount helper |
| `src/helping_hands/server/app.py` | Mount multiplayer WebSocket route |
| `frontend/src/useMultiplayer.ts` | New: React hook for yjs awareness |
| `frontend/src/useMultiplayer.test.ts` | New: Unit tests for the hook |
| `frontend/src/App.tsx` | Import hook, broadcast state, render remote players |
| `frontend/src/styles.css` | Remote player styles (color, name label, transitions) |
| `frontend/e2e/world-view.spec.ts` | E2E test for multiplayer status indicator |
| `frontend/package.json` | Added yjs, y-websocket dependencies |
| `pyproject.toml` | Added pycrdt-websocket to server extra |
| `tests/test_v273_multiplayer.py` | New: Python tests for MultiplayerRoom |

## Trade-offs

- **No authentication/authorization** on the WebSocket endpoint — acceptable for
  an internal tool; add auth middleware if exposed publicly
- **No rate limiting** — could be added to `MultiplayerRoom.broadcast()` if needed
- **Random identity per tab** — no persistent user identity; works for the
  "walk around and see each other" use case
- **Smooth transitions via CSS** — remote player movement uses 100ms CSS
  transitions rather than interpolation in JS; simpler but slightly choppy at
  very high movement speeds
