# Frontend Architecture

helping_hands has two frontend surfaces that must stay in sync.

## 1. Inline HTML UI (`server/app.py`)

A self-contained HTML/CSS/JS UI embedded in the `_UI_HTML` variable inside
`src/helping_hands/server/app.py`. Served at `GET /`.

Features:
- Task submission form (backend, model, prompt, iterations, toggles)
- JS-based polling monitor via `/tasks/{task_id}`
- No-JS fallback via `/monitor/{task_id}` (server-rendered auto-refresh)
- "Classic" and "Hand world" dashboard views
- Industrial factory/incinerator visualization in world view
- Keyboard navigation (arrows/WASD) in world view

## 2. React frontend (`frontend/`)

A React + TypeScript + Vite application in `frontend/`.

Stack:
- React 18+ with TypeScript
- Vite for build/dev
- ESLint for linting
- Vitest for testing

### Component structure

The React frontend is organized as a single-page application:

```
frontend/src/
├── main.tsx              # Entry point, renders <App />
├── App.tsx               # Main component (form, task list, monitors, world scene)
├── App.utils.ts          # Pure utility functions, fetch helpers, app-level constants
├── App.test.tsx          # App-level integration tests + Yjs awareness tests
├── App.utils.test.ts     # Utility function unit tests
├── constants.test.ts     # Constants module tests
├── constants.ts          # Shared constants (emotes, colours, scene geometry)
├── types.ts              # Shared types (25+ types: Backend, FormState, TaskStatus, etc.)
├── styles.css            # Global styles
├── vite-env.d.ts         # Vite type declarations
├── utils/
│   ├── throttledBroadcast.ts      # Leading+trailing throttle for network broadcasts
│   └── throttledBroadcast.test.ts # Throttle utility unit tests
├── components/
│   ├── FactoryFloorPanel.tsx   # Left HUD panel (name, color, presence, chat, emotes, decorations)
│   ├── FactoryFloorPanel.test.tsx # FactoryFloorPanel render + interaction tests
│   ├── HandWorldScene.tsx      # Full zen-garden scene (factory, desks, players, workers, HUD)
│   ├── HandWorldScene.test.tsx # HandWorldScene render tests
│   ├── Minimap.tsx             # Bird's-eye minimap overlay (player/worker dots)
│   ├── Minimap.test.tsx       # Minimap render tests
│   ├── MonitorCard.tsx         # Task output monitor card (tabs, filters, usage, resize)
│   ├── MonitorCard.test.tsx    # MonitorCard render + interaction tests
│   ├── PlayerAvatar.tsx        # Reusable human-player sprite component
│   ├── PlayerAvatar.test.tsx   # PlayerAvatar render tests
│   ├── AppOverlays.tsx          # Notification banner, toast container, service health bar
│   ├── AppOverlays.test.tsx    # AppOverlays render + interaction tests
│   ├── ScheduleCard.tsx        # Schedule form + list (cron presets, CRUD, toggle enable)
│   ├── ScheduleCard.test.tsx   # ScheduleCard render + interaction tests
│   ├── SubmissionForm.tsx      # Build submission form (repo, prompt, advanced settings)
│   ├── SubmissionForm.test.tsx # SubmissionForm render + field change tests
│   ├── TaskListSidebar.tsx     # Left sidebar (view toggle, nav buttons, task list)
│   ├── TaskListSidebar.test.tsx# TaskListSidebar render + interaction tests
│   ├── RemoteCursor.tsx         # SVG arrow cursor for remote player mouse position
│   ├── RemoteCursor.test.tsx   # RemoteCursor render tests
│   ├── RepoChipInput.tsx       # Chip-based input for reference repos (suggestions, keyboard nav)
│   ├── RepoChipInput.test.tsx  # RepoChipInput render + interaction tests
│   ├── RepoSuggestInput.tsx    # Text input with recent-repo suggestion dropdown
│   ├── RepoSuggestInput.test.tsx # RepoSuggestInput render + interaction tests
│   ├── WorkerSprite.tsx        # Worker sprite (bot + goose variants) with caption & floating numbers
│   └── WorkerSprite.test.tsx   # WorkerSprite render tests
├── hooks/
│   ├── useMovement.ts          # Keyboard-driven player movement hook (randomized spawn)
│   ├── useMovement.test.tsx    # Movement, collision, keyboard binding, spawn tests
│   ├── useMultiplayer.ts       # Yjs awareness multiplayer hook (join/leave notifications)
│   ├── useMultiplayer.test.tsx # Hook lifecycle, player name, join/leave notification tests
│   ├── useSceneWorkers.ts     # Scene worker lifecycle, desk slot allocation, phase timer
│   ├── useSceneWorkers.test.tsx # Worker creation, phase transitions, slot assignment, style enrichment
│   ├── useSchedules.ts        # Schedule CRUD state + operations hook
│   ├── useSchedules.test.tsx  # Schedule hook tests (load, save, delete, toggle, trigger)
│   ├── useServiceHealth.ts    # Service health polling hook (15s interval)
│   ├── useServiceHealth.test.tsx # Service health hook tests
│   ├── useClaudeUsage.ts      # Claude Code usage polling hook (1h interval + manual refresh)
│   ├── useClaudeUsage.test.tsx # Claude usage hook tests
│   ├── useRecentRepos.ts     # Recently used repos hook (localStorage, cross-tab sync)
│   ├── useRecentRepos.test.tsx # Recent repos hook tests (add, remove, dedup, cap, sync, errors)
│   ├── useTaskManager.ts      # Task submission, polling, history, output, and toasts hook
│   └── useTaskManager.test.tsx# Task manager hook tests (submit, select, poll, history, output)
└── test/
    └── setup.ts          # Vitest setup (jsdom environment)
```

### State management

State is managed via React's built-in `useState` hooks, organized into custom hooks:

- **`useTaskManager`** — Task submission, polling (primary 3s + background 10s),
  task history (localStorage persistence), form state, output tabs, floating
  numbers, toasts, worker capacity, and all derived task state
- **`useSceneWorkers`** — Scene worker lifecycle (task→worker mapping, desk slot
  allocation, phase transitions, provider style enrichment, schedule annotation)
- **`useSchedules`** — Schedule CRUD state and operations
- **`useMovement`** — Keyboard-driven player movement, collision detection
- **`useMultiplayer`** — Yjs awareness multiplayer presence, chat, decorations
- **`useServiceHealth`** — Service health polling (15-second interval)
- **`useClaudeUsage`** — Claude Code usage polling (hourly) + manual force-refresh

No external state library (Redux, Zustand, etc.) is used. State flows
top-down from hooks through `App.tsx` via props to child components.

### Key TypeScript types

| Type | Purpose |
|---|---|
| `Backend` | Union of all supported backend identifiers |
| `FormState` | Shape of the task submission form |
| `BuildResponse` | POST `/build` response |
| `TaskStatus` | GET `/tasks/{id}` response |
| `CurrentTask` | Individual task in the active queue |
| `TaskHistoryItem` | Client-side task tracking entry |

### Commands

```bash
npm --prefix frontend install
npm --prefix frontend run dev         # dev server
npm --prefix frontend run build       # production build
npm --prefix frontend run lint        # ESLint
npm --prefix frontend run typecheck   # tsc --noEmit
npm --prefix frontend run test        # Vitest
```

## Sync requirements

When modifying UI features, both surfaces must be updated:

1. Inline HTML in `_UI_HTML` (`server/app.py`)
2. React components in `frontend/src/App.tsx` + `frontend/src/styles.css`

This is documented in `AGENT.md` under Recurring decisions.

### Validating sync

To verify both surfaces offer the same features:

1. Check that any new form fields in `FormState` (React) also appear in
   the inline HTML form within `_UI_HTML`
2. Verify that new API endpoints consumed by React are also wired in the
   inline JS polling/fetch logic
3. Run both surfaces side by side:
   - Inline: `docker compose up --build` then visit `http://localhost:8000`
   - React: `npm --prefix frontend run dev` then visit `http://localhost:5173`

## Testing strategy

### Unit tests (Vitest)

- Tests live in `frontend/src/` alongside source (e.g., `App.utils.test.ts`)
- Run with `npm --prefix frontend run test`
- CI enforces: Vitest with coverage via `@vitest/coverage-v8`

### E2E tests (Playwright)

- Tests live in `frontend/e2e/` (e.g., `world-view.spec.ts`, `multiplayer.spec.ts`)
- `multiplayer.spec.ts` — multi-context tests verifying two browser windows
  each render Hand World with independent local player avatars
- Run with `npx playwright test` from `frontend/`

### Lint and type safety

- ESLint catches code quality issues: `npm --prefix frontend run lint`
- TypeScript strict mode via `tsc --noEmit`: `npm --prefix frontend run typecheck`
- Both are enforced in CI

### What to test

- Utility/helper functions extracted from components (pure logic)
- API response parsing and error handling
- Form validation logic
- Task status transition handling

## API endpoints used by both UIs

| Endpoint | Method | Purpose |
|---|---|---|
| `/build` | POST | Submit a new task |
| `/tasks/{task_id}` | GET | Get task status/result |
| `/tasks/current` | GET | List active/queued tasks |
| `/monitor/{task_id}` | GET | HTML auto-refresh monitor |
| `/workers/capacity` | GET | Celery worker pool info |
| `/ws/yjs/{room}` | WebSocket | Yjs-based multiplayer sync |
| `/health/multiplayer` | GET | Multiplayer room/connection stats |
| `/health/multiplayer/players` | GET | Connected player list with positions |

## Multiplayer Hand World

The Hand World view supports multiplayer — multiple users can walk around the
same scene and see each other's avatars in real-time.

### Architecture (Yjs — primary)

```
Browser A  ──y-websocket──┐
                           │
Browser B  ──y-websocket──▶  pycrdt-websocket ASGIServer
                           │   mounted at /ws/yjs
Browser C  ──y-websocket──┘   room: "hand-world"
```

Multiplayer sync uses **Yjs awareness** — the CRDT awareness protocol carries
ephemeral player presence (position, direction, walking state, emotes) while
the Y.Doc itself remains empty.

**Backend** (`server/multiplayer_yjs.py`):
- `pycrdt-websocket` `WebsocketServer` + `ASGIServer` mounted at `/ws/yjs`
- Handles Yjs sync and awareness protocol automatically
- Graceful fallback: if `pycrdt-websocket` is not installed, the Yjs endpoint
  is not mounted and multiplayer is disabled
- Started/stopped via FastAPI lifespan context manager

**Frontend** (`App.tsx`):
- Uses `yjs` Y.Doc + `y-websocket` WebsocketProvider for room `hand-world`
- Sets local awareness state: `{ player_id, name, color, x, y, direction, walking, emote, chat }`
- Derives player colour and name client-side from `Y.Doc.clientID`
- Maps remote awareness states to `remotePlayers` array for rendering
- Disconnected peers automatically cleaned up by Yjs awareness timeout (~30s)
- Player color customization: click a color swatch in the Factory Floor panel to pick your avatar color (persisted in localStorage)
- Emote system: press 1–4 to trigger emotes (wave, celebrate, thumbsup, sparkle)
- Emote picker panel: click the smiley button in the HUD to see all emotes with names and key bindings
- Emote bubbles float up and fade out over 2 seconds above the avatar
- Chat system: type a message in the chat input and press Enter to send
- Chat bubbles appear above the sender's avatar and fade after 4 seconds
- Idle detection: players with no movement for 30s show a floating "zzz" indicator
- Presence panel shows "(idle)" suffix next to idle players
- Player count badge: green pill badge in Hand World header showing online player count
- Typing indicator: pulsing "..." bubble when a player is typing in chat
- Smooth remote movement: CSS transitions for interpolated remote avatar motion
- Player tooltips: hover over a remote avatar to see name, color, and status
- Reconnection banner: translucent overlay with spinner when WebSocket is reconnecting

### Awareness state per client

```json
{
  "player": {
    "player_id": "42",
    "name": "Player 43",
    "color": "#e11d48",
    "x": 50, "y": 50,
    "direction": "down",
    "walking": false,
    "idle": false,
    "typing": false,
    "emote": null,
    "chat": null
  }
}
```

### Testing multiplayer locally

1. Start the backend: `docker compose up --build` or `./scripts/run-local-stack.sh start`
2. Start the dev frontend: `npm --prefix frontend run dev`
3. Open two browser windows to `http://localhost:5173`
4. Switch both to "Hand world" tab
5. Move with arrow keys — each window should show the other's avatar
