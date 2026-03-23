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

## Future extensions

- Chat bubbles above player avatars
- Redis-backed state for multi-worker deployments
- Player names from server auth context
