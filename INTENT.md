# INTENT.md

User intents and desires for the helping-hands project.

## Active Intents

(none)

## Recently Completed

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

**Implementation:** v276

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
