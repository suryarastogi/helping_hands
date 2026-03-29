# v314 — Multiplayer Leave Names & Chat Dedup Fix

**Date:** 2026-03-27
**Status:** Completed

## Goal

Fix two UX bugs in the multiplayer Hand World:

1. **Leave message name resolution** — When a player disconnects, the Yjs
   awareness `removed` event fires *after* state is already cleared, so leave
   messages fall back to generic "Player N left" instead of the player's actual
   name. Fix: cache player names from awareness updates so leave messages show
   the real name.

2. **Chat message dedup over-filtering** — The `seenRemoteChatsRef` dedup is
   keyed by `pid:text`, which means if a remote player sends the exact same
   message twice in succession, the second occurrence is silently dropped.
   Fix: incorporate a counter into the dedup key so repeated messages are
   still recorded.

## Tasks

- [x] Add `playerNamesRef` cache in `useMultiplayer` — populated on every
      awareness change from `added`/`updated` states
- [x] Use cached name in `changes.removed` handler instead of clientID fallback
- [x] Fix chat dedup key to include a sequence counter so same-text messages
      from the same player are not dropped
- [x] Add frontend tests for both fixes (2 new tests, 582 total)
- [x] Update design doc and exec plan

## Files Changed

- `frontend/src/hooks/useMultiplayer.ts`
- `frontend/src/hooks/useMultiplayer.test.tsx`
- `docs/design-docs/multiplayer-hand-world.md`
- `INTENT.md`
