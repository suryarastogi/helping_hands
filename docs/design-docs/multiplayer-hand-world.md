# Design Doc: Multiplayer Hand World

## Context

Hand World is the visualization view where users can walk around a zen garden /
factory scene using arrow keys or WASD. Previously, this was a single-player
experience — only the local user's avatar was visible.

## Decision

Add real-time multiplayer so that multiple browser windows (or different users)
can see each other's avatars walking around the scene simultaneously.

## Approach

**WebSocket over polling:** Position updates happen at 60fps during movement, so
HTTP polling would be too slow and wasteful. A persistent WebSocket connection
provides sub-100ms latency for position broadcasts.

**Server-side state:** The `WorldConnectionManager` in `server/multiplayer.py`
keeps an in-memory dict of connected players. This is simpler and faster than
using Redis pub/sub for a feature that only needs session-scoped state (no
persistence required).

**No external libraries:** The implementation uses FastAPI's built-in WebSocket
support and the browser's native `WebSocket` API. This avoids adding
dependencies like `socket.io` or `yjs` for what is a straightforward
position-broadcast use case.

**Position clamping:** The server validates and clamps all incoming coordinates
to the scene bounds before broadcasting, preventing clients from spoofing
out-of-bounds positions.

## Trade-offs

- **In-memory state** means player data is lost on server restart. This is
  acceptable since multiplayer sessions are ephemeral.
- **Single-server only** — the in-memory manager doesn't support multi-process
  deployments. If needed later, a Redis pub/sub layer can be added.
- **No authentication** — any WebSocket connection gets a player. Fine for
  internal/dev tool; would need auth for public deployment.

## Emote system (v275)

Players can trigger emotes by pressing number keys 1–4. The emote is broadcast
to all other players via a `player_emoted` message. Emotes appear as emoji
bubbles above the avatar that float up and fade out over 2 seconds.

| Key | Emote     | Emoji |
|-----|-----------|-------|
| 1   | wave      | 👋    |
| 2   | celebrate | 🎉    |
| 3   | thumbsup  | 👍    |
| 4   | sparkle   | ✨    |

Server-side validation ensures only `_VALID_EMOTES` are broadcast. Invalid
emote names are silently dropped.

## Yjs migration (v276)

The multiplayer sync layer was migrated from a bespoke JSON-over-WebSocket
protocol to **Yjs awareness**. Key changes:

- **Frontend:** Uses `yjs` Y.Doc + `y-websocket` `WebsocketProvider` connected
  to room `hand-world`. The awareness protocol carries ephemeral player state
  (position, direction, walking, emote). Colour and name are derived client-side
  from `Y.Doc.clientID` rather than being server-assigned.
- **Backend:** `pycrdt-websocket` `ASGIServer` mounted at `/ws/yjs` handles the
  Yjs sync and awareness protocol. The existing `/ws/world` endpoint is kept for
  backward compatibility but is no longer the primary connection target.
- **Benefits:** Built-in reconnect handling, automatic peer cleanup on
  disconnect (~30s timeout), CRDT-based state that auto-merges, and alignment
  with the user's preference for Yjs-powered frontends.

## Legacy endpoint removal (v278)

The original `/ws/world` custom WebSocket endpoint and `multiplayer.py` module were
deleted. The Yjs awareness endpoint at `/ws/yjs` is now the sole multiplayer sync
mechanism. A connection status indicator (green/yellow/red dot) was added to the
Hand World UI showing Yjs provider connection health.

## UX improvements (v279)

Multiplayer logic extracted from the monolithic `App.tsx` into a dedicated
`useMultiplayer` hook (`frontend/src/hooks/useMultiplayer.ts`). This hook
encapsulates all Yjs connection lifecycle, awareness sync, position broadcasting,
and emote handling.

Additional features:
- **Player name customization** — players can set a custom name via an input
  field in the Factory Floor panel. Names persist in `localStorage` and are
  broadcast via the awareness protocol without reconnecting.
- **Presence panel** — when other players are connected, a sidebar panel shows
  their names and colour indicators.
- **Shared types** — `PlayerDirection` moved to `frontend/src/types.ts` for
  reuse across App and the hook.

## Future extensions

- Chat bubbles above player avatars
- Shared Y.Doc state for persistent world features (e.g. placed objects)
- Player names from server auth context
