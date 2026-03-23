# INTENT.md

User intents and desires for the helping-hands project.

## Active Intents

### Frontend Code Quality — Types & Utils Extraction (2026-03-23)

**User request:** Continue improving multiplayer Hand World — better modularisation and code reuse.

**Implemented (v282):**
- Moved 25 types from `App.tsx` to `types.ts` (Backend, FormState, TaskStatus, ScheduleItem, etc.)
- Created `App.utils.ts` (851 lines) — 30 pure functions and 15 constants extracted from App.tsx
- Updated `App.utils.test.ts` and `WorkerSprite.tsx` to import from new modules
- App.tsx reduced from 3,590 to 2,691 lines (-899 lines)
- 245 tests passing (no regressions)

## Recently Completed

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
