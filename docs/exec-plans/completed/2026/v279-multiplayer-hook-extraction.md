# v279 — Extract Multiplayer Hook & Fix Stale Tests

**Date:** 2026-03-23
**Status:** Completed
**Scope:** Frontend multiplayer code quality & test accuracy

## Motivation

The multiplayer Yjs integration (v276–v278) works well but lived inline in the
3,900-line `App.tsx`. Extracting the ~150 lines of Yjs connection, awareness
sync, and emote logic into a dedicated `useMultiplayer` custom hook improves
maintainability and testability. Additionally, the E2E test for remote player
rendering still used the legacy `players_sync` WebSocket protocol removed in
v278.

## Tasks

- [x] Create exec plan
- [x] Extract `useMultiplayer` hook from `App.tsx` into `frontend/src/hooks/useMultiplayer.ts`
- [x] Update `App.tsx` to consume the hook instead of inline logic
- [x] Fix stale E2E test (`world-view.spec.ts`) — replaced legacy `players_sync` injection with Yjs connection status check
- [x] Add unit tests for `useMultiplayer` hook (10 tests)
- [x] Update `docs/FRONTEND.md` to document the new hook and remove legacy `/ws/world` reference
- [x] Run lint, typecheck, and tests — all 224 frontend tests pass

## Files touched

- `frontend/src/hooks/useMultiplayer.ts` (new — hook + types + constants)
- `frontend/src/hooks/useMultiplayer.test.ts` (new — 10 unit tests)
- `frontend/src/App.tsx` (removed ~150 lines of inline multiplayer logic)
- `frontend/src/App.utils.test.ts` (updated imports to point to hook)
- `frontend/e2e/world-view.spec.ts` (replaced stale legacy test)
- `docs/FRONTEND.md` (updated component tree + removed legacy references)
