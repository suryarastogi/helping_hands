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
├── main.tsx               # Entry point, renders <App />
├── App.tsx                # Main component (form, task list, monitors)
├── App.test.tsx           # Component render tests (@testing-library/react)
├── App.utils.test.ts      # Unit tests for utility functions
├── useMultiplayer.ts      # yjs awareness hook for multiplayer Hand World
├── useMultiplayer.test.ts # Tests for multiplayer hook
├── styles.css             # Global styles
├── vite-env.d.ts          # Vite type declarations
└── test/
    └── setup.ts           # Vitest setup (jsdom environment)
```

### State management

State is managed via React's built-in `useState` hooks within `App.tsx`:

- **FormState** — All form fields (repo path, prompt, backend, model, toggles)
- **TaskHistoryItem[]** — Local task history with status polling
- **WorkerCapacityResponse** — Celery worker availability
- **CurrentTasksResponse** — Active/queued tasks from server

No external state library (Redux, Zustand, etc.) is used. State flows
top-down within `App.tsx` via props to inline sub-components.

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
| `/ws/world` | WebSocket | Multiplayer awareness relay (yjs protocol) |

## Multiplayer (Hand World)

The Hand World view supports multiplayer presence — multiple browser tabs/users
can see each other's player avatars moving in real time.

### Architecture

```
Browser A ──ws──┐
                ├── FastAPI /ws/world ── MultiplayerRoom relay
Browser B ──ws──┘
```

### Frontend (yjs awareness)

- `useMultiplayer.ts` — React hook using `yjs` + `y-websocket`
- Each client creates a `Doc` + `WebsocketProvider` connected to `/ws/world`
- Local player state (position, direction, walking, color, name) is broadcast
  via the yjs awareness protocol
- Remote players are rendered as `RemotePlayer[]` with distinct colored sprites
  and name labels

### Backend (WebSocket relay)

- `src/helping_hands/server/multiplayer.py` — `MultiplayerRoom` class
- Simple binary message relay: forwards each message to all peers except sender
- No document persistence — awareness is ephemeral presence data
- Mounted on the FastAPI app via `mount_multiplayer(app)`

### Dependencies

- **Frontend:** `yjs`, `y-websocket`
- **Backend:** `pycrdt-websocket` (server extra, for future document sync features)
