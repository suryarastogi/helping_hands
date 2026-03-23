# INTENT.md

User intents and desires for the helping_hands project.

---

## 2026-03-23 — Multiplayer Hand World

**Intent:** Make the Hand World view multiplayer so that different users can walk
around and see each other's avatars in real time.

**Details:**
- Multiple browser windows/tabs should show distinct user avatars moving around
  the same Hand World scene
- Synchronization should flow through the Python backend (not peer-to-peer)
- User likes yjs-based frontend synchronization patterns
- Test plan: open multiple browsers, verify avatars move independently and are
  visible to each other

**Approach chosen:** yjs awareness protocol via WebSocket — lightweight presence
sync (position, direction, walking state, color) without full CRDT document sync.
Backend provides a WebSocket relay using `pycrdt-websocket` ASGI integration with
FastAPI. Frontend uses `yjs` + `y-websocket` for awareness.
