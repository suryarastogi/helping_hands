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

## Chat bubbles (v287)

Players can send text chat messages that appear as speech bubbles above their
avatars. Chat is broadcast via the Yjs awareness `chat` field — no new backend
endpoints are required.

**Frontend flow:**
1. A chat input appears in the Factory Floor panel when connected
2. Player types a message and presses Enter to send
3. `sendChat(text)` sets the awareness `chat` field
4. After `CHAT_DISPLAY_MS` (4 seconds), the `chat` field is cleared to `null`
5. Both local and remote players see the chat bubble above the sender's avatar
6. Chat bubbles have a float-up fade animation similar to emotes

**Constants:** `CHAT_DISPLAY_MS` (4000ms), `CHAT_MAX_LENGTH` (120 chars).

## Chat history panel (v289)

A scrollable chat history panel below the chat input retains all messages sent
during the current session. Messages are captured in the `useMultiplayer` hook
and stored in a `chatHistory` state array (capped at `CHAT_HISTORY_MAX = 50`).

**Local messages** are recorded immediately in `sendChat()`. **Remote messages**
are captured from Yjs awareness change events with deduplication — the hook
tracks `clientId:text` pairs to avoid recording the same bubble twice while it
remains in the awareness state.

The panel renders inside the Factory Floor HUD with auto-scroll to the newest
message. Each entry shows the player name (colored) and message text.

History is cleared when the player leaves the world view (hook deactivation).

## Idle/AFK detection (v290)

Players who haven't moved for `IDLE_TIMEOUT_MS` (30 seconds) are
automatically marked as idle. The idle state is broadcast via the Yjs
awareness `idle` field.

**Visual indicators:**
- A floating "zzz" label with a gentle bob animation appears above idle
  players (suppressed while an emote or chat bubble is active)
- The presence panel appends "(idle)" after idle players' names

**Implementation:**
- `useMultiplayer` tracks `lastActivityRef` (reset on any position/direction
  change) and runs a 5-second `setInterval` check
- `isLocalIdle` state is exposed for the local player and broadcast via
  awareness
- `RemotePlayer` type includes `idle: boolean` parsed from remote awareness
- `PlayerAvatar` renders `.idle-indicator` when `idle && !emote && !chat`

## Smooth remote movement (v298)

Remote player avatars now use CSS transitions for smooth position interpolation
instead of snapping between awareness updates. A `transition: left 150ms linear,
top 150ms linear` rule on `.remote-player` provides ~9fps visual interpolation
between Yjs awareness updates (which fire at ~6-10Hz). This is a pure CSS change
with no JavaScript overhead.

## Typing indicator (v298)

When a player is typing in the chat input, a pulsing "..." bubble appears above
their avatar. This is broadcast to all peers via the Yjs awareness `typing` field.

**Implementation:**
- `HandWorldScene` tracks chat input focus and content — sets `typing: true` when
  the input has focus and non-empty text, `false` on blur/clear/send
- `useMultiplayer` hook gained `setTyping()` callback, `isLocalTyping` state, and
  `remoteTyping` record
- `PlayerAvatar` renders `.typing-indicator` when `typing && !emote && !chat`
  (typing indicator takes priority over idle indicator)
- CSS: pulsing opacity animation (`typing-pulse`, 1.2s cycle) with speech-bubble
  styling matching the chat bubble design

**Awareness state:** `typing: boolean` added alongside existing `idle`, `emote`,
`chat` fields.

## Minimap (v299)

A compact bird's-eye overlay in the bottom-right corner of the scene shows all
player and worker positions at a glance. The minimap renders only when the Yjs
connection is active.

**Dot types:**
- **Local player** — white dot with glow (`minimap-dot-local`)
- **Remote players** — coloured dots matching player palette (`minimap-dot-remote`)
- **Active workers** — amber dots at desk positions (`minimap-dot-worker`)

The `Minimap` component (`frontend/src/components/Minimap.tsx`) is pure — it
receives positions as props and renders positioned `<span>` elements inside a
120×80px container with `overflow: hidden`.

## Chat cooldown (v299)

A 2-second cooldown (`CHAT_COOLDOWN_MS`) between consecutive chat messages
prevents spam. During cooldown, the chat input is disabled with a "Wait..."
placeholder. The cooldown state (`chatOnCooldown`) is managed in the
`useMultiplayer` hook and surfaced through `HandWorldScene`.

## Player list API (v300)

A new REST endpoint `GET /health/multiplayer/players` exposes connected player
details by reading Yjs awareness states server-side. This enables external tools,
dashboards, and monitoring to query who's currently online without needing a
WebSocket connection.

**Backend:**
- `get_connected_players()` in `multiplayer_yjs.py` iterates over rooms,
  reads awareness state entries (dict or JSON bytes), and extracts player
  metadata (`player_id`, `name`, `color`, `x`, `y`, `idle`)
- `_parse_awareness_state()` helper handles both in-process dict and
  JSON-encoded wire formats
- Graceful fallback: empty list when pycrdt-websocket not installed or on error

**Response:**
```json
{
  "players": [
    {"player_id": "abc", "name": "Alice", "color": "#e74c3c", "x": 50.0, "y": 50.0, "idle": false}
  ],
  "count": 1
}
```

## E2E multiplayer tests (v300)

Playwright multi-context tests verify that independent browser contexts each
render the Hand World scene with a local player avatar. Tests live in
`frontend/e2e/multiplayer.spec.ts` and cover:

- Two browser contexts both render Hand World with local player
- Player name inputs are independent per context
- Keyboard movement updates player position

## Player interaction tooltips (v301)

Hovering over a remote player avatar shows a tooltip with their name, color
indicator, and current status (active/idle/typing/walking). The tooltip appears
above the avatar with an arrow pointer.

**Implementation:**
- `PlayerAvatar` gained `showTooltip` state, toggled via `onMouseEnter`/`onMouseLeave`
- Status label derived from `typing > idle > walking > active` priority
- Tooltip only renders for remote players (`isLocal=false`), never for the local player
- CSS: `.player-tooltip` positioned above avatar with `.player-tooltip-status-{status}` color variants

## Reconnection banner (v301)

When the Yjs WebSocket connection drops and is reconnecting (`connectionStatus === "connecting"`),
a translucent overlay with a spinner and "Reconnecting…" text appears over the
entire scene. This gives clear visual feedback that sync is temporarily interrupted.

**Implementation:**
- `HandWorldScene` conditionally renders `.reconnect-banner` when connecting
- Banner uses `role="alert"` for accessibility
- CSS: translucent dark overlay (`rgba(2, 8, 23, 0.65)`) with spinner animation,
  `pointer-events: none` so the scene remains interactive underneath

## Future extensions

- Shared Y.Doc state for persistent world features (e.g. placed objects)
- Player names from server auth context
