# Week 13 (Mar 20 – Mar 28, 2026)

Multiplayer Hand World feature implementation, testing/consolidation, emotes, Yjs
migration, frontend decomposition, chat bubbles, schedule hook coverage, chat
history panel, continued component extraction (MonitorCard, SubmissionForm,
ScheduleCard, TaskListSidebar), smooth movement, typing indicators, minimap,
chat cooldown, player list API, Playwright e2e multiplayer tests, schedule
PR auto-persist, shared world decorations via Y.Map, join/leave notifications,
spawn randomization, player color customization, multiplayer hardening
(awareness validation + reconnection resilience), FactoryFloorPanel extraction,
useTaskManager hook extraction (App.tsx -61%), useSceneWorkers hook
extraction (App.tsx -47%, dead re-export cleanup), and multiplayer leave
name resolution + chat dedup fix, multiplayer cursor sharing,
useRecentRepos hook test coverage, RepoChipInput/RepoSuggestInput
component test coverage, App.tsx/useTaskManager branch coverage
improvement (both raised from below 80% to above 80%), and multiplayer
hardening edge case coverage (_clamp_float NaN/Infinity fix, client-side
cursor clamping, localStorage error handling tests, backend partial
failure tests), design doc refresh + timer cleanup + accessibility
improvements, decoration placement cooldown with backend decoration
query endpoint, AppOverlays/MonitorCard branch coverage hardening
(component stmts: 96.45% → 99.08%), remote player CSS fixes with
initial Yjs awareness position sync, and GitHub issue linking with
full-stack `issue_number` support, create-new-issue-from-task feature,
task status sync to GitHub issues (running/completed/failed lifecycle
comments via marker-tagged upsert), and GitHub Projects v2 board
integration with full-stack `project_url` support via GraphQL API,
and GitHub integration test coverage hardening (form endpoint, PR body
"Closes #N", invalid project URL edge case).

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

## Mar 23 — Extract TaskListSidebar Component (v296)

**Component extraction:** Moved inline `<aside>` sidebar block (~69 lines) into `TaskListSidebar` component. Renders dashboard view toggle (classic/world), navigation buttons, and submitted task list with status pills. 9 typed props. App.tsx: 1,575 → 1,506 lines. Updated FRONTEND.md with complete component listing.

**18 new tests, 416 frontend tests total.**

---

## Mar 23 — Extract AppOverlays Component (v297)

**Component extraction:** Moved overlay UI (~132 lines) into `AppOverlays` component. Service health bar (4 indicators + test notification button), toast container with dismiss callbacks, notification permission banner with enable/dismiss. Service worker registration and notification permission state moved into component. 3 typed props. App.tsx: 1,506 → 1,374 lines.

**15 new tests, 431 frontend tests total.**

---

## Mar 24 — Smooth Movement & Typing Indicator (v298)

**CSS smooth movement:** Added `transition: left 150ms linear, top 150ms linear` on `.remote-player` for smooth position interpolation between awareness updates. **Typing indicator:** Pulsing "..." bubble above players typing in chat. New `typing: boolean` awareness field with `setTyping()` hook API.

**10 new tests, 433 frontend tests total.**

---

## Mar 24 — Minimap & Chat Cooldown (v299)

**Minimap:** Bird's-eye overlay in bottom-right showing local (white), remote (coloured), and worker (amber) dots. **Chat cooldown:** `CHAT_COOLDOWN_MS` (2s) rate limit, input disabled during cooldown with "Wait..." placeholder.

**16 new tests, 449 frontend tests total.**

---

## Mar 24 — Player List API & E2E Multiplayer Tests (v300)

**Player list endpoint:** `GET /health/multiplayer/players` reads Yjs awareness states server-side to return connected player details (`player_id`, `name`, `color`, `x`, `y`, `idle`). New `get_connected_players()` and `_parse_awareness_state()` in `multiplayer_yjs.py`.

**Playwright e2e tests:** Multi-context tests in `frontend/e2e/multiplayer.spec.ts` verify independent browser contexts each render Hand World with local player avatars, independent name inputs, and keyboard movement.

**12 new backend tests, 3 new Playwright e2e tests.**

---

## Mar 24 — Player Tooltips & Reconnection Banner (v301)

**Player tooltips:** Hovering over remote player avatars shows tooltip with name, color indicator, and status (active/idle/typing/walking). CSS arrow pointer, remote-only rendering. **Reconnection banner:** Translucent overlay with spinner when WebSocket reconnecting. `role="alert"` accessibility, `pointer-events: none` keeps scene interactive.

**10 new tests, 459 frontend tests total.**

---

## Mar 24 — Emote Picker Panel (v302)

**Emote picker:** Smiley button in HUD toggles 2×2 grid of emote buttons (emoji, name, shortcut). Click triggers `onTriggerEmote(key)` and auto-closes. Hidden when disconnected.

**5 new tests, 464 frontend tests total.**

---

## Mar 26 — Multiplayer Coverage Hardening (v303)

**Coverage improvement:** Added 2 tests for `setTyping` callback and remote typing state tracking in `useMultiplayer` hook. Branch coverage: 81% → 82.35%. Overall: 466 frontend tests.

---

## Mar 26 — Schedule PR Auto-Persist (v304)

**Auto-persist newly created PRs:** When a scheduled task with no `pr_number` creates a new PR, the PR number is automatically saved back to the schedule so subsequent runs push to the same PR instead of creating new ones. `Hand.last_pr_metadata` attribute stores finalization metadata. `ScheduleManager.update_pr_number()` for focused writes. `_maybe_persist_pr_to_schedule()` helper with guard conditions. Non-E2E results now include PR metadata.

**18 new tests (4 ScheduleManager, 7 celery helper, 7 hand instantiation).**

---

## Mar 26 — Shared World Decorations via Y.Map (v305)

**Persistent shared state:** First use of Y.Map document state in the multiplayer world. Players can place emoji decorations (8 emoji palette, 20 cap) that all connected players see in real-time. Decoration toolbar in Factory Floor panel with emoji selection, count, and clear button. Double-click scene to place. Pop animation on placement.

**16 new tests (6 hook, 10 scene). 482 frontend tests total.**

---

## Mar 26 — Player Avatar Color Customization (v307)

**Color picker:** Players can choose their avatar color from the 10-color palette instead of auto-assignment from clientID. Color persists in localStorage. Broadcast via Yjs awareness without reconnecting. Color picker row with swatch buttons in Factory Floor panel.

**6 new tests (3 hook, 3 scene). 493 frontend tests total.**

---

## Mar 26 — Multiplayer Hardening (v308)

**Awareness validation:** Server-side `validate_awareness_state()` clamps positions [0,100], coerces types, truncates names/chat, strips control chars, validates direction enum. `get_player_activity_summary()` returns active/idle breakdown. `get_connected_players()` now validates states. New `GET /health/multiplayer/activity` endpoint.

**Reconnection resilience:** Frontend tracks reconnect attempts; after 10 consecutive failures, transitions to "failed" terminal state and disconnects provider. "Connection failed" banner with red overlay.

**30 new backend tests, 7 new frontend tests. 500 frontend tests total.**

---

## Mar 26 — Join/Leave Notifications & Spawn Randomization (v306)

**Multiplayer UX:** System messages in chat history for player join/leave events. Randomized spawn positions within padded bounds to prevent avatar overlap.

**5 new tests. 487 frontend tests total.**

---

## Mar 26 — Extract FactoryFloorPanel Component (v309)

**Component extraction:** Extracted `FactoryFloorPanel` (~180 lines) from HandWorldScene — contains player name/color customization, presence panel, connection status, emote picker, chat input/history, and decoration toolbar. HandWorldScene: 618 → 437 lines.

**36 new tests in `FactoryFloorPanel.test.tsx`. 535 frontend tests total.**

---

## Mar 26 — Extract useTaskManager Hook (v310)

**Major App.tsx decomposition:** Extracted task submission, polling, history management, output tab, floating numbers, toasts, and all derived task state into a dedicated `useTaskManager` hook (~500 lines). App.tsx reduced from 1,374 to 538 lines (-836 lines, -61%). This is the single largest extraction in the decomposition series.

**17 new tests in `useTaskManager.test.tsx`. 553 frontend tests total.**

---

## Mar 26 — Extract useSceneWorkers Hook (v311)

**Final App.tsx decomposition:** Extracted scene worker lifecycle management (~210 lines) into `useSceneWorkers` hook. Manages worker state, desk slot allocation, phase timer, provider style enrichment, and schedule annotation. Removed 48 lines of dead re-exports. App.tsx reduced from 538 to 313 lines (-42%).

**16 new tests in `useSceneWorkers.test.tsx`. 569 frontend tests total.**

---

## Mar 27 — Multiplayer Perf & Backend Awareness Fix (v313)

**Backend fix:** `get_connected_players()` and `get_player_activity_summary()` now correctly extract the `player` sub-dict from nested Yjs awareness state before validation. Health endpoints were returning empty/default values. New `_extract_player_state()` helper with flat-format fallback. Fixed lifecycle tests for pycrdt-websocket >= 0.16 API.

**Frontend perf:** `POSITION_BROADCAST_INTERVAL_MS` (60ms) throttle on position broadcasts — leading+trailing pattern reduces network traffic for multi-user sessions.

**8 new backend tests, 2 new frontend tests. 580 frontend tests, 63 backend multiplayer tests.**

---

## Mar 27 — Multiplayer Leave Names & Chat Dedup Fix (v314)

**Two UX bug fixes:** Leave messages now show the player's actual name instead of "Player N left" — a `playerNamesRef` cache in `useMultiplayer` retains name/color from awareness updates since state is already cleared by the time Yjs fires `removed`. Chat dedup fixed: per-player sequence counter bumped on bubble expiry so the same message text sent again is properly recorded instead of being silently dropped.

**2 new frontend tests. 582 frontend tests total.**

---

## Mar 27 — Multiplayer Cursor Sharing (v315)

**Cursor sharing:** Remote players' mouse cursors visible as colored SVG arrow pointers with name labels in the Hand World scene. Broadcast via Yjs awareness `cursor` field, throttled to 100ms. New `RemoteCursor` component, `updateCursor()` hook API, `onMouseMove`/`onMouseLeave` scene handlers. CSS smooth interpolation (80ms transitions).

**11 new frontend tests (4 hook, 4 scene, 3 component). 593 frontend tests total.**

---

## Mar 27 — Cursor Broadcast Throttle Coverage (v316)

**Coverage:** 3 tests for `updateCursor()` throttle behavior — rapid updates throttled with trailing broadcast, immediate broadcast when window elapsed, null cancels timer.

**3 new frontend tests. 596 frontend tests total.**

---

## Mar 27 — useRecentRepos Hook Test Coverage (v317)

**Coverage:** 16 tests for `useRecentRepos` hook — the last custom hook without co-located tests. Covers initial state loading, add/dedup/cap, whitespace handling, remove, cross-tab sync via StorageEvent, invalid/non-array JSON resilience, and localStorage error handling.

**16 new frontend tests. 612 frontend tests total.**

---

## Mar 27 — RepoChipInput & RepoSuggestInput Test Coverage (v318)

**Coverage:** Added co-located tests for the two remaining untested frontend components. RepoChipInput (26 tests): chip add/remove, keyboard navigation, suggestion filtering, duplicate prevention, whitespace handling, dropdown limit. RepoSuggestInput (19 tests): suggestion dropdown, keyboard navigation, mouse selection, filtering, autoComplete, highlight reset. Updated FRONTEND.md component listing.

**45 new frontend tests. 657 frontend tests total.**

---

## Mar 27 — App.tsx & useTaskManager Branch Coverage (v319)

**App.tsx (69.23% → 81.25% branch):** 4 new tests covering `fetchServerConfig()` effect branches. **useTaskManager.ts (72.03% → 82.68% branch):** 13 new tests covering submit body, poll error handling, terminal status toast, query-string initialization, output tab modes, current tasks discovery. Overall branch coverage: 88.55% → 90.23%.

**17 new frontend tests. 674 frontend tests total.**

---

## Mar 27 — Multiplayer Hardening & Edge Case Coverage (v320)

**Frontend:** 4 localStorage error handling tests, client-side cursor position clamping (coordinates clamped to [0,100] before broadcasting), 1 decoration null-guard test. **Backend:** 10 edge case tests (_clamp_float NaN/Infinity, _strip_control_chars emoji preservation, _parse_awareness_state invalid UTF-8, _extract_player_state empty/list, partial iteration failures). **Bug fix:** `_clamp_float` now returns midpoint for NaN, clamps ±Infinity to bounds.

**7 new frontend tests (681 total), 10 new backend tests (84 total).**

---

## Mar 27 — Design Doc Refresh & Multiplayer Resilience (v321)

**Design doc refresh:** Rewrote "Approach" section in `multiplayer-hand-world.md` — removed deleted `WorldConnectionManager` and "No external libraries" references, updated to Yjs architecture. **Timer cleanup:** 5 new timeout refs tracked in `useMultiplayer` (emote, chat, cooldown timers), cleared on lifecycle cleanup. Rapid emote triggers cancel previous timer. **Accessibility:** `aria-live` on reconnection/failed banners, `aria-label` on refresh button, `aria-hidden` on RemoteCursor SVG, status in PlayerAvatar remote aria-label.

**10 new frontend tests (691 total).**

---

## Mar 27 — Decoration Placement Cooldown & Decoration Query Endpoint (v322)

**Decoration cooldown:** Added `DECO_COOLDOWN_MS` (1500ms) constant and cooldown logic to `placeDecoration` in `useMultiplayer` hook — prevents rapid decoration spam. Decoration emoji buttons disabled during cooldown. Double-click placement blocked during cooldown. `decoOnCooldown` state threaded through `HandWorldScene` and `FactoryFloorPanel`.

**Backend decoration endpoint:** Added `get_decoration_state()` to `multiplayer_yjs.py` — reads Y.Map from room's Y.Doc, validates/clamps positions, strips control chars. New `GET /health/multiplayer/decorations` endpoint in `app.py`.

**7 new frontend tests (698 total), 6 new backend tests (90 total).**

---

## Mar 27 — AppOverlays & MonitorCard Branch Coverage (v323)

**AppOverlays coverage (83.53% → 98.17% stmts):** 6 new tests covering the `testNotification()` function: Notification API unavailable triggers alert, permission not granted triggers requestPermission, permission granted without SW reg uses new Notification() constructor, constructor throws triggers alert, requestPermission rejection handled gracefully, Enable button calls requestPermission.

**MonitorCard coverage (85.46% → 100% stmts):** 13 new tests covering prefix filter chip cycling (show→hide→only→show), Reset button, task error banner rendering, cancel button (confirm+fetch, decline, error swallowed), copy to clipboard, prefix chip icons.

**19 new frontend tests (717 total). Overall: 97.06% stmts, 90.47% branches.**

---

## Mar 27 — Remote Player CSS Fixes & Initial Position Sync (v324)

**CSS fixes:** Consolidated duplicate `transition` on `.remote-player` (150ms + 80ms → single 150ms). Fixed `pointer-events: none` → `auto` for tooltip hover. **Initial position sync:** `useMultiplayer` awareness now uses actual spawn position from `useMovement` instead of hardcoded (50, 50).

**3 new frontend tests (720 total).**

---

## Mar 28 — GitHub Issue Linking (v325)

**Full-stack issue linking:** Added `issue_number` field through the entire stack (frontend FormState → SubmissionForm → useTaskManager → BuildRequest → Celery task → Hand base class). PR body includes "Closes #N" for auto-close on merge, comment posted on issue with PR link. `GitHubClient.get_issue()` and `create_issue_comment()` methods. Frontend issue number field in Advanced settings with URL query param support.

**14 new tests (10 backend, 4 frontend). 724 frontend tests total, 92 backend GitHub tests.**

---

## Mar 28 — Create New Issue from Task (v326)

**Issue creation from tasks:** Added `GitHubClient.create_issue()` method. New `create_issue` boolean field through full stack — when enabled and no `issue_number` is provided, a new GitHub issue is automatically created from the task prompt before the hand runs. The created issue number is then used for PR linking ("Closes #N") just like manually-provided issue numbers. Frontend checkbox in Advanced settings.

*(Test counts updated after implementation)*

---

## Mar 28 — Sync Task Status with GitHub Issue (v328)

**Issue status lifecycle sync:** `_sync_issue_status()` helper posts or updates a marker-tagged comment on the linked GitHub issue at key lifecycle points: 🔄 running (hand starts), ✅ completed (with PR URL), ❌ failed (with error). Uses `upsert_pr_comment()` with `<!-- helping_hands:issue_status -->` marker for idempotent updates. Best-effort: errors swallowed.

**5 new tests. 127 celery tests total (up from 122), 7501 backend tests.**

---

## Mar 28 — GitHub Projects Board Integration (v329)

**Full-stack project integration:** Added `project_url` field through the entire stack (frontend → backend → Celery task). `GitHubClient.add_to_project_v2()` uses GitHub GraphQL API (`addProjectV2ItemById` mutation) to add linked issues to GitHub Projects v2 boards. `parse_project_url()` parses org/user project URLs. `_try_add_to_project()` Celery helper is best-effort. Frontend Project URL input in Advanced settings.

**15 new tests (11 backend, 4 frontend). 7516 backend tests total.**

---

## Mar 28 — GitHub Integration Test Coverage (v330)

**Integration test hardening:** Filled coverage gaps in the v325–v329 GitHub integration feature stack. TestBuildForm: 2 new tests for `issue_number` and `create_issue`+`project_url` form submission. TestCreateNewPrIssueClose: 2 new tests for PR body "Closes #N" generation. TestTryAddToProject: 1 new test for invalid project URL graceful failure.

**5 new tests. 6439 backend tests total (up from 6433).**

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
- `v296-extract-task-list-sidebar.md`
- `v297-extract-app-overlays.md`
- `v298-multiplayer-smooth-movement-typing-indicator.md`
- `v299-minimap-chat-cooldown.md`
- `v300-multiplayer-e2e-and-player-list-api.md`
- `v301-player-tooltips-reconnect-banner.md`
- `v302-emote-picker-panel.md`
- `v303-multiplayer-coverage-hardening.md`
- `v304-schedule-pr-auto-persist.md`
- `v305-shared-world-decorations.md`
- `v306-join-leave-notifications-spawn-randomization.md`
- `v307-player-color-customization.md`
- `v308-multiplayer-hardening.md`
- `v309-factory-floor-panel-extraction.md`
- `v310-extract-use-task-manager.md`
- `v311-extract-use-scene-workers.md`
- `v312-extract-polling-hooks.md`
- `v313-multiplayer-perf-and-backend-fix.md`
- `v314-multiplayer-leave-names-chat-dedup.md`
- `v315-multiplayer-cursor-sharing.md`
- `v316-cursor-throttle-coverage.md`
- `v317-use-recent-repos-coverage.md`
- `v318-repo-input-components-test-coverage.md`
- `v319-app-task-manager-coverage.md`
- `v320-multiplayer-hardening-edge-cases.md`
- `v321-design-doc-refresh-timer-cleanup.md` (→ `2026-03-27-design-doc-refresh.md`)
- `v322-decoration-cooldown-and-decoration-endpoint.md`
- `v323-appoverlays-monitorcard-coverage.md`
- `v324-multiplayer-css-fixes-and-spawn-sync.md`
- `v325-github-issue-linking.md`
- `v326-create-issue-from-task.md`
- `v328-sync-issue-status.md`
- `v329-github-projects-integration.md`
- `v330-github-integration-test-coverage.md`
