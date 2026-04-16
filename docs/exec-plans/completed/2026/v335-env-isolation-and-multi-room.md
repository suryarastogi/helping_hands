# v335 — Test Env Isolation & Multi-Room Multiplayer

**Status:** completed
**Created:** 2026-04-17
**Completed:** 2026-04-17

## Goal

Two self-contained improvements:

1. **Fix test env leakage** — five tests fail in any shell that exports
   `HELPING_HANDS_CI_MAX_RETRIES`, `HELPING_HANDS_CLI_HEARTBEAT_SECONDS`,
   `HELPING_HANDS_*_USE_NATIVE_CLI_AUTH`, etc., because those values
   override the stub/config defaults the tests assert against. Add an
   autouse conftest fixture that scrubs these knobs for the duration of
   every test. CI was green only because its shell happens not to set
   them.

2. **Multi-room multiplayer Hand World** — today every user lands in the
   same `"hand-world"` Yjs room. Add a `room` option to `useMultiplayer`
   (fallback `"hand-world"`) and read a `?world=<slug>` URL param so
   small groups can share a private world without running separate
   servers. Room slug is sanitised (`[a-zA-Z0-9_-]`, max 40 chars) before
   being handed to `y-websocket`, so a hostile URL can't inject colons
   into the WebSocket path. No backend changes — `pycrdt-websocket`
   already isolates state per room.

## Tasks

- [x] Add `tests/conftest.py` autouse `_scrub_env_isolation` fixture
- [x] Verify 5 previously failing tests now pass
- [x] Add `room?: string` option to `UseMultiplayerOptions`, default `"hand-world"`
- [x] Export `sanitizeWorldRoom()` helper + `DEFAULT_WORLD_ROOM` constant
- [x] Read `?world=<slug>` in `App.tsx`, pass sanitised value down
- [x] Render room name badge in Hand World header when non-default
- [x] Add `useMultiplayer` tests: custom room, default fallback, sanitisation
- [x] Add `App.test.tsx` test: URL param flows into the provider
- [x] Update `docs/design-docs/multiplayer-hand-world.md` (multi-room section)
- [x] Update `docs/FRONTEND.md` room option reference
- [x] Update `INTENT.md` + `PLANS.md`

## Results

- Autouse `_scrub_env_isolation` fixture in `tests/conftest.py` removes seven
  `HELPING_HANDS_*` env vars that dev shells commonly export; full backend
  suite now passes regardless of dev env state
- `useMultiplayer` now accepts a `room` option; `sanitizeWorldRoom()` helper
  and `DEFAULT_WORLD_ROOM = "hand-world"` constant exported from the same
  module
- `App.tsx` reads `?world=<slug>` via `URLSearchParams` and threads the
  sanitised value into `useMultiplayer` + `HandWorldScene`
- Non-default rooms render a `#<slug>` badge next to the Hand World heading
  with `.world-room-badge` styling (mirrors `.player-count-badge`)
- 18 new frontend tests added (10 hook, 5 App URL-routing, 3 scene badge)
  covering custom room, fallback, sanitisation, badge rendering, and URL
  param flow
- Backend 6542 tests, frontend 754 tests (736 → 754), all green

## Completion criteria

- 5 previously failing tests green (env isolation)
- Backend suite still passes (≥75% coverage gate)
- Frontend suite still passes, 736 → ~745+
- Hand World reachable via both `/?world=team-a` and default URL
- Invalid world slug silently falls back to default (no crash / no colon injection)
