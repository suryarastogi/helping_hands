# INTENT.md

User intents and desires for the helping-hands project.

## Active Intents

### OAuth Token Test Fix & Credentials Coverage (2026-03-29) — Completed

Fixed 16 broken `_get_claude_oauth_token` tests across 3 test files — the
addition of `_read_claude_credentials_file()` as a first-try path caused tests
that only mock `subprocess.run` to find a real token before the mock was reached.
Added 6 new tests (5 `_read_claude_credentials_file` + 1 credentials-file-first
path). See [v336 plan](docs/exec-plans/active/v336-oauth-token-test-fix-and-credentials-coverage.md).

## Recently Completed

### ModelProvider Coverage Hardening (2026-03-29) — Completed

Close remaining coverage gaps in `model_provider.py`: `_require_langchain_class`
direct tests, provider-name resolution branches, empty model validation. Also
fixed pre-existing `test_env_var_forwarding` env leak. See
[v335 plan](docs/exec-plans/completed/2026/v335-model-provider-coverage-hardening.md).

### GooseCLIHand & CLIHandBase Coverage Hardening (2026-03-29) — Completed

Close testable coverage gaps in `GooseCLIHand` (88% → 99%) and `CLIHandBase`
(98% → 99%). See [v334 plan](docs/exec-plans/completed/2026/v334-goose-cli-base-coverage.md).

### DevinCLIHand & Factory Coverage Hardening (2026-03-28) — Completed

**Implemented (v333):**
- 15 new DevinCLIHand tests (35 total, up from 20): `_inject_prompt_argument`, `_normalize_base_command`, `_native_cli_auth_env_names`, `_describe_auth`, `_permission_mode`, `_apply_backend_defaults`
- 8 new `get_enabled_backends` tests (58 factory tests total, up from 50)
- 6485 backend tests passed, 0 failures, 75.87% coverage

## Previously Completed

### Validation & Task Result Coverage Hardening (2026-03-28) — Completed

**Implemented (v332):**
- Fixed v331 plan structure conformance (`## Completed Tasks` → `## Tasks`)
- Added 4 `require_non_empty_string` TypeError tests: int, None, bool, list inputs
- Added 5 `require_positive_int` TypeError tests: bool (True/False), float, string, None inputs
- Added 6 `format_type_error` direct unit tests: param name, expected type, actual type, None, dict, custom class
- Added 5 `normalize_task_result` edge case tests: empty status, whitespace status, None status, int status, non-serializable object fallback
- 20 new tests total (15 validation, 5 task_result), all passing
- 6459 backend tests passed, 0 failures, 78.28% coverage

### Server Module Test Coverage Hardening (2026-03-28) — Completed

**Implemented (v331):**
- Added 4 `_ProgressEmitter` direct unit tests: `emit()` with defaults, overrides, preserving non-overridden fields, multiple sequential calls
- Added 1 `_resolve_repo_path` TimeoutExpired branch test: mock subprocess timeout raises `ValueError`, verifies temp dir cleanup
- Added 1 `_setup_periodic_tasks` signal handler test: verifies delegation to `ensure_usage_schedule()`
- Added 4 `_load_meta` corrupted data tests: invalid JSON, warning log, missing required fields, empty required field
- 10 new tests total (6 celery_app, 4 schedule_manager), all passing

### GitHub Integration Test Coverage (2026-03-28) — Completed

**Implemented (v330):**
- Added integration-level tests for v325–v329 GitHub features
- `TestBuildForm`: 2 tests for `issue_number`, `create_issue`, and `project_url` form submission
- `TestCreateNewPrIssueClose`: 2 tests verifying PR body "Closes #N" generation (with and without issue_number)
- `TestTryAddToProject`: 1 test for invalid `project_url` graceful failure
- 5 new tests total

### Deeper GitHub Integration (2026-03-28) — Completed

~~Features Wanted:~~
- ~~a checkbox (like fix ci) "Project Management" which feeds/enables GitHub Issues and Projects integration~~
    - ~~When creating a task, option to link to an existing GitHub issue or create a new issue from the task (with task prompt as issue body)~~ **v325: issue_number field added — links task to existing issue via "Closes #N" in PR body + comment on issue**
    - ~~When creating a task, option to create a new issue from the task (with task prompt as issue body)~~ **v326: create_issue checkbox — auto-creates GitHub issue from task prompt, then links it to the PR**
    - ~~Sync task status with GitHub issue with created PR~~ **v328: _sync_issue_status() posts running/completed/failed status comments on linked issue via marker-tagged upsert**
    - ~~GitHub Projects board integration~~ **v329: full-stack `project_url` support — add issues to GitHub Projects v2 boards via GraphQL API after creation/linking**

### GitHub Projects Board Integration (2026-03-28) — Completed

**Implemented (v329):**
- `GitHubClient.add_to_project_v2()` method — resolves project/content node IDs via GraphQL, calls `addProjectV2ItemById` mutation
- `parse_project_url()` static method — parses org/user project URLs into (owner_type, owner, number)
- `_graphql()` private helper — executes GitHub GraphQL queries via `urllib.request`
- `project_url` field added to full stack: frontend FormState → SubmissionForm → useTaskManager → BuildRequest → Celery `build_feature` task
- `_try_add_to_project()` helper in `celery_app.py` — best-effort wrapper, errors logged but never block the build
- After issue creation/linking and before hand execution, linked issue is added to the specified project
- Frontend: Project URL input in Advanced settings, URL query param support (`?project_url=...`)
- 15 new tests (11 backend, 4 frontend), 7516 backend tests passed, 0 failures

### Sync Task Status with GitHub Issue (2026-03-28) — Completed

**Implemented (v328):**
- `_sync_issue_status()` helper in celery_app.py — posts or updates a marker-tagged comment on the linked GitHub issue at key lifecycle points
- "running" status posted when hand starts execution
- "completed" status posted after success, includes PR URL
- "failed" status posted on exception, includes truncated error message
- Uses `upsert_pr_comment()` with `<!-- helping_hands:issue_status -->` marker for idempotent updates (same comment updated, not new ones created)
- Best-effort: sync failures are logged but never block the build
- 5 new backend tests (127 celery tests total, up from 122)
- 7501 backend tests passed, 0 failures

### Fix Test Failures & Form Param Gap (2026-03-28) — Completed

**Implemented (v327):**
- Fixed 9 test failures introduced by v325–v326 feature additions
- Added missing `issue_number` and `create_issue` Form parameters to `enqueue_build_form`
  — the inline HTML form handler was missing these fields from v325/v326
- Fixed plan structure conformance for v324–v326 completed plans (status metadata,
  section headings, PLANS.md entry format)
- Updated 5 `TestBuildForm` expected dicts with new fields
- 6426 tests passed, 0 failures, 78.48% coverage

### Sync Task Status with GitHub Issue (2026-03-28) — Completed

**Implemented (v327):**
- `GitHubClient.add_issue_labels()` — adds labels to a GitHub issue, auto-creating labels that don't exist on the repo
- `GitHubClient.remove_issue_label()` — removes a label from an issue (silently ignores if not present)
- `_sync_issue_started()` helper in `celery_app.py` — adds `helping-hands:in-progress` label when task begins running
- `_sync_issue_completed()` helper — posts completion comment with PR link + runtime, swaps label to `helping-hands:completed`, removes `in-progress`
- `_sync_issue_failed()` helper — posts failure comment with error details, swaps label to `helping-hands:failed`, removes `in-progress`
- All sync helpers are error-tolerant: failures are logged but never block the build
- `issue_number` included in Celery progress metadata so frontend can track it during polling
- `linkedIssueNumber` computed in `useTaskManager` hook from payload
- MonitorCard shows blue `#N` issue badge in header when a linked issue is present
- `taskInputs` includes `Issue: #N` when issue number is in the payload
- 7 new backend tests (3 GitHubClient label methods, 8 celery sync helpers = 11 total backend)
- 4 new frontend tests (2 MonitorCard badge, 2 useTaskManager linkedIssueNumber)
- 104 backend GitHub tests (up from 97), 80+ celery tests, 732 frontend tests (up from 728)

### Create New Issue from Task (2026-03-28) — Completed

**Implemented (v326):**
- `GitHubClient.create_issue()` method — creates a new issue via PyGithub API with title, body, and optional labels
- `create_issue` boolean field added to full stack: frontend FormState → SubmissionForm checkbox → useTaskManager → BuildRequest → Celery `build_feature` task
- `_try_create_issue()` helper in `celery_app.py` — when `create_issue=True` and no `issue_number` is provided, auto-creates a GitHub issue with `[helping-hands]` prefixed title (first 120 chars of prompt) and full prompt as body, applies `helping-hands` label
- Created issue number flows into existing `issue_number` pipeline — PR gets "Closes #N" and issue gets PR link comment
- Error handling: issue creation failures are logged and reported in task updates but don't block the build
- Frontend: "Create issue" checkbox in Advanced settings, URL query param support (`?create_issue=true`)
- 5 new backend tests (GitHubClient.create_issue: 3 success + 2 validation), 4 Celery helper tests
- 4 new frontend tests (2 SubmissionForm checkbox, 2 useTaskManager submit body)
- 728 frontend tests total (up from 724), 97 backend GitHub tests (up from 92)

### GitHub Issue Linking (2026-03-28) — Completed

**Implemented (v325):**
- `issue_number` field added to full stack: frontend FormState → SubmissionForm → useTaskManager → BuildRequest → Celery task → Hand base class
- `GitHubClient.get_issue()` and `create_issue_comment()` methods for issue API operations
- PR body automatically includes "Closes #N" when issue number is provided — GitHub auto-closes the issue on merge
- Comment posted on the linked issue with a link to the created/updated PR
- Error handling: issue comment failures are logged but don't block PR creation
- Works with both new PRs (`_create_new_pr`) and existing PR updates (`_push_to_existing_pr`)
- Frontend: issue number field in Advanced settings, URL query param support (`?issue_number=42`)
- 10 new backend tests (4 GitHubClient, 3 _post_issue_link_comment, 2 issue_number attribute, 1 create_issue_comment validation)
- 4 new frontend tests (2 SubmissionForm, 2 useTaskManager)
- 724 frontend tests total (up from 720), 92 backend tests in test_github.py (up from 78)

### Remote Player CSS Fixes & Initial Position Sync (2026-03-27) — Completed

**Implemented (v324):**
- Fixed duplicate CSS `transition` on `.remote-player` — two declarations (150ms and 80ms) with second silently overriding first; consolidated to single 150ms transition
- Fixed `pointer-events: none` on `.remote-player` — changed to `pointer-events: auto` so hover tooltips (added in v301) actually work in real browsers (unit tests passed because `fireEvent` bypasses CSS)
- Fixed initial Yjs awareness position hardcoded to (50, 50) — now uses actual spawn position from `useMovement` via `playerPosition` option, preventing remote players from briefly seeing wrong initial position
- Initial awareness direction and walking state also sync from options instead of hardcoded defaults
- 3 new frontend tests verifying initial position/direction/walking sync in awareness state
- 720 frontend tests total (up from 717)

### AppOverlays & MonitorCard Branch Coverage (2026-03-27) — Completed

**Implemented (v323):**
- Added 6 `AppOverlays` tests covering `testNotification()` branches: Notification API unavailable (alert fallback), permission not granted (requests permission), permission granted without SW reg (new Notification constructor), Notification constructor throws, requestPermission rejection, Enable button calls requestPermission
- Added 13 `MonitorCard` tests: prefix filter cycling (show→hide→only→show), Reset button, task error banner rendering, cancel button (confirm+fetch, decline, fetch error swallowed), copy to clipboard, prefix chip icons for show/hide/only modes
- AppOverlays.tsx: 83.53% → 98.17% statements
- MonitorCard.tsx: 85.46% → 100% statements
- 717 frontend tests total (up from 698), overall 97.06% statements, 90.47% branches

### Decoration Placement Cooldown & Decoration Query Endpoint (2026-03-27) — Completed

**Implemented (v322):**
- Added `DECO_COOLDOWN_MS` (1500ms) decoration placement cooldown to prevent spam — mirrors the existing chat cooldown pattern
- `decoOnCooldown` state in `useMultiplayer` hook, threaded through `HandWorldScene` and `FactoryFloorPanel`
- Decoration emoji buttons disabled during cooldown, double-click scene placement blocked during cooldown
- `decoCooldownTimerRef` added to lifecycle cleanup to prevent state updates after unmount
- Backend `get_decoration_state()` endpoint (`GET /health/multiplayer/decorations`) — reads Y.Map from room Y.Doc, validates/clamps positions, strips control chars, returns sorted list
- 698 frontend tests total (up from 691), 90 backend multiplayer tests (up from 84)

### Design Doc Refresh & Multiplayer Resilience (2026-03-27) — Completed

**Implemented (v321):**
- Refreshed multiplayer design doc "Approach" section — removed references to deleted `WorldConnectionManager` and "No external libraries", updated to reflect Yjs architecture
- Fixed timer cleanup in `useMultiplayer` hook — 5 new timeout refs (emoteTimerRef, emoteAwarenessTimerRef, chatDisplayTimerRef, chatAwarenessTimerRef, chatCooldownTimerRef) tracked and cleared on connection lifecycle cleanup, preventing state updates on destroyed providers
- Rapid emote triggers now cancel previous emote timer instead of leaving orphaned timeouts
- Accessibility improvements across 6 components: `aria-live="polite"` on reconnection banner, `aria-live="assertive"` on failed banner, `aria-label` on refresh button, `aria-hidden` on RemoteCursor SVG, PlayerAvatar remote aria-label includes status (e.g. "Alice (walking)"), improved Minimap aria-label
- 691 frontend tests total (up from 681), all passing

### Multiplayer Hardening & Edge Case Coverage (2026-03-27) — Completed

**Implemented (v320):**
- Fixed `_clamp_float` NaN/Infinity handling — NaN returns midpoint, ±Infinity clamps to bounds instead of propagating
- Added client-side cursor position clamping in `updateCursor` — coordinates now clamped to [0, 100] before broadcasting, matching backend validation
- 7 new frontend tests: localStorage error handling (SecurityError/QuotaExceededError) for load/save name/color, clearDecorations null-doc guard, cursor clamping, non-numeric cursor filtering
- 10 new backend tests: _clamp_float (Infinity, NaN, numeric strings), _strip_control_chars (emoji preservation), _parse_awareness_state (invalid UTF-8, bytearray), _extract_player_state (empty dict, list), get_connected_players partial iteration failure
- 681 frontend tests total (up from 674), 84 backend multiplayer tests (up from 74)

### App.tsx & useTaskManager Branch Coverage (2026-03-27) — Completed

**Implemented (v319):**
- Added 4 tests for `App.tsx` server config effect branches — `native_auth_default`, `enabled_backends` filtering, backend replacement when current not in filtered list, `claude_native_cli_auth === false` hiding usage panel, and URL param skip
- Added 13 tests for `useTaskManager.ts` — submit body optional fields, poll error handling, terminal status toast, query-string initialization (`task_id`, `status`, `error`, form params), output tab modes, current tasks discovery, runtime display, task inputs derivation
- `App.tsx` branch coverage: 69.23% → 81.25%
- `useTaskManager.ts` branch coverage: 72.03% → 82.68%
- Overall frontend branch coverage: 88.55% → 90.23%
- 674 frontend tests total (up from 657)

### RepoChipInput & RepoSuggestInput Test Coverage (2026-03-27) — Completed

**Implemented (v318):**
- Added 26 tests for `RepoChipInput` component — chip add/remove, keyboard navigation (Enter, Tab, comma, Backspace, ArrowUp/Down, Escape), suggestion filtering, duplicate prevention, whitespace trim, dropdown limit (8), outside click close, mouse selection, container click focus
- Added 19 tests for `RepoSuggestInput` component — suggestion dropdown, keyboard navigation, mouse selection, filtering, outside click, autoComplete, highlight reset on typing, dropdown limit (8)
- Updated FRONTEND.md component listing with RepoChipInput, RepoSuggestInput, and RemoteCursor
- 657 frontend tests total (up from 612)

### useRecentRepos Hook Test Coverage (2026-03-27) — Completed

**Implemented (v317):**
- Added 16 tests for `useRecentRepos` hook — the last custom hook without co-located tests
- Tests cover: initial state from localStorage, add/dedup/cap at 20, trim whitespace, empty string no-op, remove, cross-tab sync via StorageEvent, invalid JSON resilience, non-array fallback, non-string filtering, localStorage error handling (SecurityError, QuotaExceededError)
- 612 frontend tests total (up from 596)
- Updated FRONTEND.md hook listing with useRecentRepos test file

### Cursor Broadcast Throttle Coverage (2026-03-27) — Completed

**Implemented (v316):**
- Added 3 new tests for `updateCursor()` throttle behavior in `useMultiplayer` hook
- Test: rapid cursor updates within `CURSOR_BROADCAST_INTERVAL_MS` are throttled with trailing broadcast
- Test: cursor broadcasts immediately when throttle window has elapsed
- Test: `updateCursor(null)` cancels pending throttle timer and broadcasts immediately
- 596 frontend tests total (up from 593)

### Multiplayer Cursor Sharing (2026-03-27) — Completed

**Implemented (v315):**
- Remote players' mouse cursors visible in the Hand World scene as colored SVG arrow pointers with name labels
- Cursor position broadcast via Yjs awareness `cursor` field (throttled to 100ms)
- `RemoteCursor` component with smooth CSS transition interpolation (80ms)
- `useMultiplayer` hook: `updateCursor()` callback + `remoteCursors` state
- `HandWorldScene`: `onMouseMove` / `onMouseLeave` handlers convert to scene-relative percentages
- 11 new frontend tests (4 hook, 4 scene, 3 component), 593 total (up from 582)

### Multiplayer Leave Names & Chat Dedup Fix (2026-03-27) — Completed

**Implemented (v314):**
- Fixed leave message name resolution: `useMultiplayer` now caches player names/colors from awareness updates in `playerNamesRef`, so leave system messages show the player's actual name (e.g. "Alice left") instead of generic "Player N left"
- Fixed chat dedup over-filtering: per-player sequence counter (`chatSeqRef`) bumped when a chat bubble expires, so the same message text sent again is recorded as a new message instead of being silently dropped
- 2 new frontend tests (582 total, up from 580)

### Multiplayer Performance & Backend Awareness Fix (2026-03-27) — Completed

**Implemented (v313):**
- Fixed backend awareness state extraction bug: `get_connected_players()` and `get_player_activity_summary()` now correctly extract the `player` sub-dict from nested Yjs awareness state (`{player: {player_id, name, ...}}`) before validation — health endpoints were previously returning empty/default values for all players
- Added `_extract_player_state()` helper with backwards-compatible flat-format fallback
- Fixed lifecycle tests to match pycrdt-websocket >= 0.16 (`__aenter__`/`__aexit__`)
- Added frontend position broadcast throttling (`POSITION_BROADCAST_INTERVAL_MS = 60ms`) — leading+trailing throttle reduces network traffic for multi-user sessions without visible lag
- 8 new backend tests (63 total, up from 61)
- 2 new frontend tests, 580 frontend tests total (up from 579)

### Extract useServiceHealth & useClaudeUsage Hooks (2026-03-26) — Completed

**Implemented (v312):**
- Extracted `useServiceHealth` hook — 15-second polling interval, returns `ServiceHealthState | null`
- Extracted `useClaudeUsage` hook — 1-hour polling interval + manual `refreshClaudeUsage()` callback
- App.tsx reduced from 313 to 271 lines (-42 lines, -13%)
- Both new hooks at 100% statement and branch coverage
- 10 new tests (4 useServiceHealth, 6 useClaudeUsage)
- All 579 frontend tests pass (up from 569)

### Extract useSceneWorkers Hook (2026-03-26) — Completed

**Implemented (v311):**
- Extracted `useSceneWorkers` hook (~210 lines) from App.tsx — scene worker lifecycle, desk slot allocation, phase timer, provider style enrichment, schedule annotation
- App.tsx reduced from 538 to 313 lines (-225 lines, -42%)
- Removed 48 lines of dead re-exports from App.tsx (nothing imported them from `"./App"`)
- `SceneWorkerEntry` type consolidated: defined in hook, re-exported from HandWorldScene
- 16 new tests in `useSceneWorkers.test.tsx`
- All 569 frontend tests pass (up from 553)

### Extract useTaskManager Hook (2026-03-26) — Completed

**Implemented (v310):**
- Extracted `useTaskManager` hook (~500 lines) from App.tsx — task submission, polling, history, output, toasts
- App.tsx reduced from 1,374 to 538 lines (-836 lines, -61%)
- 17 new tests in `useTaskManager.test.tsx`
- All 553 existing frontend tests pass

### Extract FactoryFloorPanel Component (2026-03-26) — Completed

**Implemented (v309):**
- Extracted `FactoryFloorPanel` component (~180 lines) from HandWorldScene — contains player name/color customization, presence panel, connection status, emote picker, chat input/history, and decoration toolbar
- HandWorldScene.tsx reduced from 618 to 437 lines (-181 lines)
- `FactoryFloorPanelProps` typed interface with 18 props
- Chat input state, emote picker state, auto-scroll, and form submit logic moved into panel
- `selectedDecoEmoji` state remains in HandWorldScene (needed for scene `deco-placing` class + double-click handler)
- 36 new tests in `FactoryFloorPanel.test.tsx`
- All 535 existing tests pass (1 pre-existing flaky WASD test excluded)

### Multiplayer Hardening — Awareness Validation & Reconnection Resilience (2026-03-26) — Completed

**Implemented (v308):**
- Server-side `validate_awareness_state()` utility — clamps positions to [0,100], coerces types, truncates names (50 chars) and chat (120 chars), strips control characters, validates direction enum
- `get_player_activity_summary()` endpoint (`GET /health/multiplayer/activity`) — returns active/idle breakdown with fully validated player states
- `get_connected_players()` now uses validation pipeline for hardened player list API
- Frontend reconnection resilience: tracks reconnect attempts, transitions to "failed" terminal state after 10 consecutive failures, disconnects provider to prevent infinite retry loops
- "Connection failed" banner with red overlay in HandWorldScene
- `reconnectAttempts` exposed in `useMultiplayer` return value
- 30 new backend tests (validation, clamping, sanitization, activity summary)
- 7 new frontend tests (5 reconnection hook, 2 scene failed banner) — 500 frontend tests total

### Player Avatar Color Customization (2026-03-26) — Completed

**Implemented (v307):**
- Color picker in Factory Floor panel with 10-color swatch palette
- Players choose their avatar color instead of auto-assignment from clientID
- Color persists in localStorage via `loadPlayerColor()` / `savePlayerColor()`
- Color changes broadcast via Yjs awareness without reconnecting
- 6 new tests (3 hook, 3 scene) — 493 frontend tests total

### Join/Leave Notifications & Spawn Randomization (2026-03-26) — Completed

**Implemented (v306):**
- Join/leave system messages in chat history via Yjs awareness `change` event `added`/`removed` arrays
- System messages render with italic/muted styling (`.chat-history-system` class)
- Randomized player spawn positions within padded `OFFICE_BOUNDS` to prevent avatar overlap
- `randomSpawnPosition()` utility + `SPAWN_PADDING` constant
- 5 new tests (3 multiplayer join/leave, 1 spawn bounds, 1 scene system message) — 487 frontend tests total

### Shared World Decorations (2026-03-26) — Completed

**Implemented (v305):**
- Persistent shared decorations in multiplayer Hand World using Y.Map document state
- 8-emoji palette (🌸⭐🔥💡🎵❤️🌱💎), 20 decoration max
- Decoration toolbar in Factory Floor panel with count, emoji selection, and clear button
- Double-click scene to place selected emoji at click position
- Pop animation on placement, crosshair cursor during placement mode
- Y.Map observation syncs decorations to all connected players in real-time
- No backend changes needed (pycrdt-websocket auto-syncs Y.Doc)
- 16 new tests (6 hook, 10 scene) — 482 frontend tests total

### Schedule PR Auto-Persist (2026-03-26) — Completed

**Implemented (v304):**
- When a scheduled task with no `pr_number` creates a new PR, the PR number is
  auto-persisted back to the schedule for subsequent runs
- `Hand.last_pr_metadata` attribute on base class
- `ScheduleManager.update_pr_number()` focused write method
- `_maybe_persist_pr_to_schedule()` helper with guard conditions
- `build_feature` task gains optional `schedule_id` parameter
- Non-E2E hand results now include PR metadata (`**hand.last_pr_metadata`)
- 18 new tests (4 ScheduleManager, 7 celery helper, 7 hand instantiation)

### Multiplayer Coverage Hardening (2026-03-26) — Completed

**Implemented (v303):**
- Added 2 tests for `setTyping` callback and remote typing state tracking in `useMultiplayer` hook
- `useMultiplayer.ts` branch coverage: 81.18% → 82.35%
- Overall frontend: 466 tests (up from 464), 86.89% branches (up from 86.78%)
- Updated Week-13 consolidation with v301–v303

### Emote Picker Panel (2026-03-24) — Completed

**Implemented (v302):**
- Visual emote picker panel: smiley button in HUD toggles a 2x2 grid of emote buttons
- Each button shows emoji, name (wave/celebrate/thumbsup/sparkle), and keyboard shortcut (1–4)
- Clicking an emote triggers it and auto-closes the panel
- `onTriggerEmote` prop added to HandWorldScene, wired from useMultiplayer's triggerEmote
- Panel and button hidden when disconnected
- 5 new tests → 464 frontend tests total (up from 459)
- Updated FRONTEND.md and daily consolidation

### Player Tooltips & Reconnection Banner (2026-03-24) — Completed

**Implemented (v301):**
- Player interaction tooltips: hover over remote avatar shows name, color dot, and status (active/idle/typing/walking)
- Reconnection banner: translucent overlay with spinner when WebSocket is reconnecting
- Tooltip only renders for remote players, never local — with CSS arrow pointer
- Banner uses `role="alert"` for accessibility, `pointer-events: none` to keep scene interactive
- 10 new tests (7 PlayerAvatar tooltip, 3 HandWorldScene banner)
- 459 frontend tests total (up from 449)
- Updated design doc and FRONTEND.md

### Multiplayer Polish: Minimap & Chat Cooldown (2026-03-24) — Completed

**Implemented (v299):**
- Minimap component: bird's-eye overlay showing local player (white), remote players (coloured), and active workers (amber) as positioned dots
- Chat cooldown: 2-second rate limit (`CHAT_COOLDOWN_MS`) between messages, input disabled during cooldown with "Wait..." placeholder
- `Minimap` component in `frontend/src/components/Minimap.tsx`
- `chatOnCooldown` state in `useMultiplayer` hook, threaded through `HandWorldScene` props
- 16 new tests: 6 Minimap, 3 useMultiplayer cooldown, 7 HandWorldScene (minimap + cooldown)
- 449 frontend tests total (up from 433)
- Updated design doc and FRONTEND.md

### Multiplayer Smooth Movement & Typing Indicator (2026-03-24) — Completed

**Implemented (v298):**
- CSS transition on `.remote-player` for smooth position interpolation (150ms linear)
- Typing indicator: pulsing "..." bubble above players who are typing in chat
- `typing` field added to Yjs awareness state
- `useMultiplayer` hook gained `setTyping()`, `isLocalTyping`, `remoteTyping`
- `PlayerAvatar` renders `.typing-indicator` (suppressed by emote/chat, takes priority over idle)
- 10 new tests (433 frontend tests total, up from 423)
- Updated design doc and FRONTEND.md

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
