# Week 13 (Mar 20 – Mar 26, 2026)

Multiplayer Hand World feature implementation, testing/consolidation, emotes, Yjs
migration, frontend decomposition, chat bubbles, schedule hook coverage, chat
history panel, and continued component extraction (MonitorCard, SubmissionForm,
ScheduleCard).

---

## Mar 23 — Multiplayer Hand World (v273)

**Full-stack multiplayer view:** Added real-time multiplayer to Hand World so multiple users see each other's avatars. Backend: `WorldConnectionManager` in `multiplayer.py` with `/ws/world` WebSocket endpoint — player join/leave/move broadcasting, position clamping, color assignment, 20-player capacity. Frontend: WebSocket client in `App.tsx` with `RemotePlayer` state management, 50ms throttled position updates, auto-reconnect. CSS: `.remote-player` with directional sprites, walking animations, name tags.

**Protocol:** `players_sync` (full state on connect), `player_joined`, `player_left`, `player_moved`. No external deps.

**13 backend tests.** Design doc: `docs/design-docs/multiplayer-hand-world.md`. Frontend doc: `docs/FRONTEND.md` updated with multiplayer architecture.

---

## Mar 23 — Multiplayer Testing & Consolidation (v274)

**Frontend Vitest tests:** 9 multiplayer component tests using MockWebSocket — verifies players_sync rendering, player join/leave/move, dedup protection, cleanup on view change, malformed message resilience. 3 additional wsUrl edge case tests.

**E2E test:** Best-effort remote player rendering test in `world-view.spec.ts`.

**Docs:** Daily and weekly consolidation. Multiplayer intent marked completed.

**12 new tests.**

---

## Mar 23 — Multiplayer Emotes (v275)

**Emote system:** Players press keys 1–4 to trigger emotes (wave, celebrate, thumbsup, sparkle). Backend validates against `_VALID_EMOTES` and broadcasts `player_emoted` to others. Frontend renders emoji bubbles with float-up + fade-out CSS animation (2s duration). Emote hint shown in multiplayer status panel.

**7 backend tests + 2 frontend tests.**

---

---

## Mar 23 — Yjs Multiplayer Sync (v276)

**Awareness protocol migration:** Replaced custom WebSocket protocol with Yjs awareness. Backend: `pycrdt-websocket` ASGIServer at `/ws/yjs`. Frontend: `yjs` + `y-websocket` WebsocketProvider. Ephemeral player presence via awareness layer, color/name from `Y.Doc.clientID`.

---

## Mar 23 — Multiplayer Test Coverage (v277)

**Edge-case hardening:** Backend tests for unknown player noop, missing fields, boundary values, double disconnect, dead connection cleanup, Yjs globals. Frontend Yjs awareness mock tests for all multiplayer interactions.

---

## Mar 23 — Legacy WebSocket Cleanup & Connection Status (v278)

**Dead code removal:** Deleted `multiplayer.py` and `test_multiplayer.py`. Removed `/ws/world` route — Yjs is now sole sync mechanism.

**Connection status UI:** Yjs provider status tracking with green/yellow/red indicator dot. Removed unused `myPlayerId` state. **4 new tests, 211 total passing.**

---

## Mar 23 — Multiplayer UX Improvements (v279)

**Hook extraction:** Extracted `useMultiplayer` hook from monolithic App.tsx (~150 lines of inline multiplayer logic). Player name customization with localStorage persistence. Connected players presence panel showing online users with colour indicators.

**11 new tests, 222 total passing.**

---

## Mar 23 — Extract Constants & PlayerAvatar Component (v280)

**Module decoupling:** Extracted `constants.ts` with emote, colour, and scene-geometry constants — `useMultiplayer.ts` no longer imports from `App.tsx`. Created shared `PlayerAvatar` component eliminating duplicate human-body sprite tree between local and remote player renders.

**11 new tests, 233 total passing.**

---

## Mar 23 — Extract WorkerSprite Component (v281)

**Component extraction:** Extracted `WorkerSprite` component with goose + bot sprite variants and internal `GooseBody`/`BotBody` sub-components. Moved `WorkerVariant`, `CharacterStyle`, `SceneWorkerPhase`, `FloatingNumber` types to `types.ts`. Removed ~220 lines of inline sprite markup from App.tsx.

**12 new tests, 245 total passing.**

---

## Mar 23 — Extract App Types & Utils (v282)

**Major extraction:** Moved 25 types from `App.tsx` to `types.ts`. Created `App.utils.ts` (~851 lines) with 30 pure functions and 15 constants. App.tsx reduced from 3,590 to 2,691 lines (-899 lines).

**245 tests passing.**

---

## Mar 23 — Extract HandWorldScene Component (v283)

**Scene extraction:** Extracted `HandWorldScene` component (~250 lines of scene JSX) from App.tsx. App.tsx reduced from 2,691 to 2,462 lines (-229 lines).

**15 new tests, 260 total passing.**

---

## Mar 23 — Decompose Test Files (v284)

**Test co-location:** Split monolithic `App.test.tsx` (2,395 lines) into 7 co-located test files matching component structure. New files: `constants.test.ts`, `PlayerAvatar.test.tsx`, `WorkerSprite.test.tsx`, `HandWorldScene.test.tsx`, `useMultiplayer.test.tsx`. App.test.tsx reduced to 1,804 lines (App-level + Yjs awareness tests only).

**260 tests across 7 files (no regressions).**

---

## Mar 23 — Extract useSchedules Hook (v285)

**Hook extraction:** Extracted `useSchedules` hook — all schedule CRUD state (5 state vars) and 8 handler functions (load, save, delete, toggle, trigger, edit, cancel, updateField) moved from App.tsx. App.tsx reduced from 2,462 to 2,275 lines (-187 lines).

**13 new tests, 273 total passing.**

---

## Mar 23 — Extract useMovement Hook (v286)

**Hook extraction:** Extracted `useMovement` hook — keyboard input (arrow keys + WASD), position clamping within office bounds, desk collision detection, direction and walking state. App.tsx reduced from 2,275 to 2,179 lines (-96 lines). Fixed stale legacy `/ws/world` references in FRONTEND.md.

**8 new tests, 281 total passing.**

---

## Mar 23 — Multiplayer Chat Bubbles (v287)

**Chat feature:** Players send text messages via input field, displayed as speech bubbles above avatars. Chat broadcast via Yjs awareness `chat` field — no new backend endpoints. `CHAT_DISPLAY_MS` (4s) auto-clear, `CHAT_MAX_LENGTH` (120 chars). Chat input appears in Factory Floor panel when connected.

**13 new tests, 294 total passing.**

---

## Mar 23 — useSchedules Branch Coverage (v288)

**Coverage hardening:** Added 9 tests covering error paths, edit mode, and optional fields in `useSchedules` hook. Coverage: 81% → 100% statements, 60% → 95% branches. Overall frontend: 88.46% → 89.57% statements, 80.26% → 82.67% branches.

**9 new tests, 303 total passing.**

---

## Mar 23 — Chat History Panel (v289)

**Chat history:** Added scrollable chat history panel to Hand World so players can review past messages. `ChatMessage` type, `CHAT_HISTORY_MAX` (50) constant. `useMultiplayer` hook tracks both local and remote messages with deduplication. Panel renders in Factory Floor HUD with auto-scroll and player-colored names. History cleared on deactivation.

**8 new tests, 311 total passing.**

---

## Mar 23 — Player Idle/AFK Detection (v290)

**Idle detection:** Players with no movement for 30s marked idle. Floating "zzz" indicator above idle avatars with bob animation (suppressed when emote/chat active). Presence panel shows "(idle)" suffix. `useMultiplayer` tracks `lastActivityRef` with 5s interval check. Broadcast via Yjs awareness `idle` field.

**13 new tests, 324 total passing.**

---

## Mar 23 — Multiplayer Hook Branch Coverage (v291)

**Coverage hardening:** Targeted uncovered branches across multiplayer hooks and HandWorldScene. HandWorldScene: 89% → 100% branches (fully covered). useMovement: 89% → 96.5% branches. useMultiplayer: 72% → 81% branches. Overall frontend: 84.1% branches, 90.1% statements.

**14 new tests, 338 total passing.**

---

## Mar 23 — Multiplayer Stats Endpoint & Player Count Badge (v292)

**Observability & UX:** Added `get_multiplayer_stats()` to `multiplayer_yjs.py` — queries Yjs WebsocketServer for room/connection counts with defensive fallbacks. New `GET /health/multiplayer` endpoint. Frontend: player-count badge (green pill) in Hand World header showing online count when connected. CSS `.player-count-badge`.

**9 new tests (5 backend, 4 frontend), 342 frontend tests total.**

---

## Mar 23 — Extract MonitorCard Component (v293)

**Component extraction:** Moved inline `monitorCard` JSX (~146 lines) into `MonitorCard` component. Output tabs, prefix filters, usage display, cancel button, resizable pane, task inputs.

**19 new tests, 361 frontend tests total.**

---

## Mar 23 — Extract SubmissionForm Component (v294)

**Component extraction:** Moved inline `submissionCard` JSX (~152 lines) into `SubmissionForm` component. Repo path, prompt, Run button, Advanced settings (backend, model, iterations, checkboxes, token, reference repos). Props: `form`, `onFieldChange`, `onSubmit`. App.tsx: 2,043 → 1,891 lines.

**17 new tests, 378 frontend tests total.**

---

## Mar 23 — Extract ScheduleCard Component (v295)

**Component extraction:** Moved inline schedule form and schedule list JSX (~316 lines) into `ScheduleCard` component with internal `ScheduleFormFields` sub-component. 16 typed props covering schedule CRUD callbacks, form state, and error display. App.tsx: 1,891 → 1,575 lines.

**20 new tests, 398 frontend tests total.**

---

## Individual plan files

- `v273-multiplayer-hand-world.md`
- `v274-multiplayer-testing-consolidation.md`
- `v275-multiplayer-emotes.md`
- `v276-yjs-multiplayer-sync.md`
- `v277-multiplayer-test-coverage.md`
- `v278-legacy-ws-cleanup-connection-status.md`
- `v279-multiplayer-ux-improvements.md`
- `v280-extract-constants-player-avatar.md`
- `v281-extract-worker-sprite.md`
- `v282-extract-app-types-utils.md`
- `v283-extract-hand-world-scene.md`
- `v284-decompose-test-files.md`
- `v285-extract-use-schedules-hook.md`
- `v286-extract-use-movement-hook.md`
- `v287-multiplayer-chat-bubbles.md`
- `v288-use-schedules-branch-coverage.md`
- `v289-chat-history-panel.md`
- `v290-player-idle-detection.md`
- `v291-multiplayer-hook-branch-coverage.md`
- `v292-multiplayer-stats-player-count.md`
- `v293-extract-monitor-card.md`
- `v294-extract-submission-form.md`
- `v295-extract-schedule-card.md`
