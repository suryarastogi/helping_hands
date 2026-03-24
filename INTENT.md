# INTENT.md

User intents and desires for the helping-hands project.

## Active Intents

Deeper GitHub integration - Features Wanted:
- a checkbox (like fix ci) "Project Management" which feeds/enables GitHub Issues and Projects integration
    - When creating a task, option to link to an existing GitHub issue or create a new issue from the task (with task prompt as issue body)
    - Sync task status with GitHub issue with created PR
- if pr number is empty on a scheduled task it should create the PR the first time and on subsequent runs it should update the same PR (this might be easiest to achieve by unscheduling and rescheduling the task with the same PR number)



## Recently Completed

### Extract AppOverlays Component (2026-03-23) — Completed

**Implemented (v297):**
- Extracted `AppOverlays` component from App.tsx (~132 lines)
- Component handles: service health bar, toast notifications, notification permission banner, test notification button
- Moved service worker registration and notification permission state into AppOverlays
- Props interface: `AppOverlaysProps` with 3 typed props
- App.tsx reduced from 1,506 to 1,374 lines (-132 lines)
- 15 new tests in `AppOverlays.test.tsx` (health bar states, toasts, notification banner)
- 431 frontend tests total (up from 416)

### Extract TaskListSidebar Component (2026-03-23) — Completed

**Implemented (v296):**
- Extracted `TaskListSidebar` component from inline sidebar JSX in App.tsx (~69 lines)
- Component renders: view toggle (classic/world), nav buttons, submitted task list with status pills
- Props interface: `TaskListSidebarProps` with 9 typed props
- App.tsx reduced from 1,575 to 1,506 lines (-69 lines)
- 18 new tests in `TaskListSidebar.test.tsx` (view toggle, button callbacks, task rendering, selection, clear)
- 416 frontend tests total (up from 398)
- Updated FRONTEND.md component listing with SubmissionForm, ScheduleCard, TaskListSidebar

### Extract ScheduleCard Component (2026-03-23) — Completed

**Implemented (v295):**
- Extracted `ScheduleCard` component from inline schedule form + list JSX in App.tsx (~316 lines)
- Internal `ScheduleFormFields` sub-component for reuse in new/edit modes
- Props interface: `ScheduleCardProps` with 16 typed props
- App.tsx reduced from 1,891 to 1,575 lines (-316 lines)
- 20 new tests in `ScheduleCard.test.tsx` (rendering, callbacks, form states, error display, toggle, delete, edit, trigger)
- 398 frontend tests total (up from 378)

### Extract SubmissionForm Component (2026-03-23) — Completed

**Implemented (v294):**
- Extracted `SubmissionForm` component from inline `submissionCard` JSX in App.tsx (~152 lines)
- Component renders repo path, prompt, Run button, and Advanced settings panel (backend, model, iterations, checkboxes, token, reference repos)
- Props interface: `SubmissionFormProps` with `form`, `onFieldChange`, `onSubmit`
- App.tsx reduced from 2,043 to 1,891 lines (-152 lines)
- 17 new tests in `SubmissionForm.test.tsx` (rendering, field change callbacks, form submission, checkbox toggles, backend select)
- 378 frontend tests total (up from 361)

### Extract MonitorCard Component (2026-03-23) — Completed

**Implemented (v293):**
- Extracted `MonitorCard` component from inline `monitorCard` JSX in App.tsx (~146 lines)
- Component handles output tabs, prefix filters, accumulated usage, cancel button, resize, task inputs
- Props interface: `MonitorCardProps` with 17 typed props
- App.tsx reduced from 2,189 to 2,043 lines (-146 lines)
- 19 new tests in `MonitorCard.test.tsx` (tab rendering, selection, callbacks, cancel visibility, prefix filters, usage, blinker states, resize)
- 361 frontend tests total (up from 342)

### Multiplayer Observability & UX Polish (2026-03-23) — Completed

**Implemented (v292):**
- Backend: `get_multiplayer_stats()` in `multiplayer_yjs.py` — queries Yjs WebsocketServer for room/connection counts
- Backend: `GET /health/multiplayer` endpoint in `app.py` — returns `{available, rooms, connections}`
- Frontend: Player count badge in Hand World header — shows online count when connected
- CSS: `.player-count-badge` — green pill badge with player count
- 5 backend tests (stats: unavailable, empty rooms, multiple rooms, exception handling)
- 4 frontend tests (badge shown/hidden per connection status, correct count with remotes)
- 342 frontend tests total (up from 338), 13 backend multiplayer tests (up from 8)

### Multiplayer Hook Branch Coverage (2026-03-23) — Completed

**Implemented (v291):**
- Targeted uncovered branches in useMovement, useMultiplayer, and HandWorldScene
- HandWorldScene.tsx: 89% → 100% branch coverage (fully covered)
- useMovement.ts: 89% → 96.5% branch coverage
- useMultiplayer.ts: 72% → 81% branch coverage
- Overall frontend: 82.5% → 84.1% branches
- 14 new tests (338 total, up from 324)

### Player Idle/AFK Detection (2026-03-23) — Completed

**Implemented (v290):**
- Added `IDLE_TIMEOUT_MS` (30s) constant — players marked idle after 30s of no movement
- `useMultiplayer` hook tracks `lastActivityRef` and broadcasts `idle` via Yjs awareness
- `PlayerAvatar` renders floating "zzz" indicator (suppressed when emote/chat active)
- Presence panel shows "(idle)" suffix next to idle remote players
- CSS bob animation for idle indicator
- 13 new tests (324 total, up from 311)

### Chat History Panel (2026-03-23) — Completed

**Implemented (v289):**
- Added `ChatMessage` type and `CHAT_HISTORY_MAX` (50) constant
- `useMultiplayer` hook now tracks chat history (local + remote messages via Yjs awareness)
- Deduplication of repeated awareness updates for the same message
- Scrollable chat history panel in HandWorldScene with auto-scroll, player-colored names
- History cleared on world view deactivation
- 8 new tests (311 total, up from 303)

## Recently Completed

### useSchedules Branch Coverage (2026-03-23) — Completed

**Implemented (v288):**
- Added 9 tests to `useSchedules.test.tsx` covering error paths, edit mode, optional fields
- `useSchedules.ts` coverage: 81% → 100% statements, 60% → 95% branches
- Overall frontend coverage: 88.46% → 89.57% statements, 80.26% → 82.67% branches
- 303 tests total (up from 294)

### Multiplayer Chat Bubbles (2026-03-23) — Completed

**Implemented (v287):**
- Added text chat to Hand World — players send messages via input field, displayed as speech bubbles above avatars
- Chat broadcast via Yjs awareness `chat` field (no new backend endpoints)
- `CHAT_DISPLAY_MS` (4s) auto-clear, `CHAT_MAX_LENGTH` (120 chars)
- Chat input appears in Factory Floor panel when connected
- 13 new tests across constants, PlayerAvatar, HandWorldScene, and useMultiplayer

### Frontend Code Quality — Movement Hook Extraction (2026-03-23) — Completed

**Implemented (v286):**
- Extracted `useMovement` hook — keyboard input, position clamping, collision detection, direction/walking state
- App.tsx reduced from 2,275 to 2,179 lines (-96 lines)
- 8 new tests for movement hook (281 total, up from 273)
- Fixed stale legacy `/ws/world` references in FRONTEND.md

### Frontend Code Quality — Schedule Hook Extraction (2026-03-23) — Completed

**Implemented (v285):**
- Extracted `useSchedules` hook — schedule CRUD state (5 state vars) and 8 handler functions
- App.tsx reduced from 2,462 to 2,275 lines (-187 lines)
- 13 new tests for schedule hook (273 total, up from 260)

### Frontend Code Quality — Test File Decomposition (2026-03-23) — Completed

**Implemented (v284):**
- Split monolithic `App.test.tsx` (2,395 lines) into 7 co-located test files
- New files: `constants.test.ts`, `PlayerAvatar.test.tsx`, `WorkerSprite.test.tsx`, `HandWorldScene.test.tsx`, `useMultiplayer.test.tsx`
- App.test.tsx reduced from 2,395 to 1,804 lines (-591 lines, App-level + Yjs awareness tests only)
- 260 tests across 7 files (no regressions)

### Frontend Code Quality — HandWorldScene Extraction (2026-03-23) — Completed

**Implemented (v283):**
- Extracted `HandWorldScene` component (~250 lines of scene JSX) from `App.tsx`
- Scene renders zen garden, factory, incinerator, desks, player avatars, worker sprites, and HUD panels
- App.tsx reduced from 2,691 to 2,462 lines (-229 lines)
- 15 new tests (260 total, up from 245)

### Frontend Code Quality — Types & Utils Extraction (2026-03-23) — Completed

**Implemented (v282):**
- Moved 25 types from `App.tsx` to `types.ts` (Backend, FormState, TaskStatus, ScheduleItem, etc.)
- Created `App.utils.ts` (851 lines) — 30 pure functions and 15 constants extracted from App.tsx
- Updated `App.utils.test.ts` and `WorkerSprite.tsx` to import from new modules
- App.tsx reduced from 3,590 to 2,691 lines (-899 lines)
- 245 tests passing (no regressions)

### Frontend Code Quality — WorkerSprite Component Extraction (2026-03-23) — Completed

**Implemented (v281):**
- Extracted `WorkerSprite` component — goose + bot sprite variants with internal `GooseBody`/`BotBody` sub-components
- Moved `WorkerVariant`, `CharacterStyle`, `SceneWorkerPhase`, `FloatingNumber` types to `types.ts`
- Removed ~220 lines of inline sprite markup from `App.tsx`
- 12 new tests (245 total, up from 233)

### Frontend Code Quality — Constants & Component Extraction (2026-03-23) — Completed

**Implemented (v280):**
- Extracted `constants.ts` — emote, colour, and scene-geometry constants decoupled from App.tsx
- Extracted `PlayerAvatar` component — shared sprite tree for local and remote players
- `useMultiplayer.ts` no longer imports from `App.tsx`
- 11 new tests (233 total, up from 222)

### Multiplayer UX Improvements (2026-03-23) — Completed

**User request:** Continue improving the multiplayer Hand World experience — better code structure, player identity, and presence awareness.

**Implemented (v279):**
- Extracted `useMultiplayer` hook from monolithic App.tsx (reduced ~150 lines of inline logic)
- Player name customization with localStorage persistence
- Connected players presence panel showing online users with color indicators
- 11 new tests (222 total, up from 211)

### Yjs Multiplayer Synchronisation (2026-03-23) — Completed

**User request:** Migrate Hand World multiplayer sync to use Yjs. The user likes frontends that use Yjs for real-time collaboration. Synchronisation should flow through the Python backend.

**Requirements:**
- Replace custom WebSocket protocol with Yjs awareness protocol
- Use `yjs` + `y-websocket` on the frontend
- Use `pycrdt-websocket` on the Python backend
- Multiple browser windows should still see each other's avatars and emotes
- Testable by opening multiple browsers

**Technical direction:**
- Backend: `pycrdt-websocket` ASGIServer mounted at `/ws/yjs`
- Frontend: Yjs awareness for ephemeral player presence (position, emotes)
- Color/name derived client-side from Yjs clientID

**Implementation:** v276, v278 (legacy cleanup + connection status)

## Completed Intents

### Multiplayer Hand World (2026-03-23) — Completed

**User request:** In `frontend/`, make Hand World a multiplayer view so that different users can walk around Hand World. Multiple users should see each other's avatars moving in real-time.

**Requirements:**
- Different browser windows/tabs should show multiple user avatars
- Each user gets a unique avatar with distinct color
- Synchronization should be done through the Python backend via WebSocket
- Inspired by frontends that use Yjs for real-time collaboration
- Testable by opening multiple browsers and seeing avatars move

**Technical direction:**
- Backend: FastAPI WebSocket endpoint for player position broadcast
- Frontend: WebSocket client that sends/receives player positions
- Simple protocol: join → position updates → leave
- No external dependencies for sync (lightweight custom protocol over WebSocket)

**Implementation:** v273 (backend + frontend + CSS), v274 (testing + consolidation)
