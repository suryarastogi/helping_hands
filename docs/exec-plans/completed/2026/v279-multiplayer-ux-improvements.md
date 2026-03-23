# v279 — Multiplayer UX Improvements

**Status:** Completed
**Created:** 2026-03-23
**Completed:** 2026-03-23
**Intent:** Improve Hand World multiplayer experience with better code organization, player identity, and presence awareness.

## Context

The Yjs-based multiplayer system (v273–v278) is functional: players see each other, move around, and emote. However:

1. All multiplayer logic lives inline in the 3988-line `App.tsx` monolith
2. Player names are anonymous ("Player 123" derived from clientID)
3. No persistent player identity across sessions
4. No visible player list showing who's connected

## Tasks

- [x] **Extract `useMultiplayer` hook** — Moved Yjs connection, awareness sync, position broadcasting, and emote logic into `frontend/src/hooks/useMultiplayer.ts`.
- [x] **Player name customization** — Added localStorage-persisted player name with input field in Factory Floor panel. Names broadcast via awareness without reconnecting.
- [x] **Connected players panel** — Added presence list showing connected player names + color indicators.
- [x] **Tests** — 11 new tests (222 total, up from 211). Hook lifecycle, player name persistence, presence panel rendering, emote triggering.
- [x] **Docs update** — Updated INTENT.md, multiplayer design doc, moved plan to completed.

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/hooks/useMultiplayer.ts` | New: extracted multiplayer hook |
| `frontend/src/types.ts` | New: shared `PlayerDirection` type |
| `frontend/src/App.tsx` | Refactored: replaced ~150 lines of inline Yjs logic with hook consumption |
| `frontend/src/styles.css` | Added: player name input + presence panel styles |
| `frontend/src/App.test.tsx` | Added: 11 new tests for hook + presence + player name |
| `INTENT.md` | Updated: recorded v279 completion |
| `docs/design-docs/multiplayer-hand-world.md` | Updated: documented v279 architecture |

## Acceptance Criteria — All Met

1. `useMultiplayer` hook encapsulates all Yjs logic; App.tsx just consumes its return values
2. Players can set a custom name that persists across browser sessions via localStorage
3. Connected players panel shows names and color indicators when others are online
4. All 222 frontend tests pass (11 new, 0 regressions)
5. Lint passes with 0 warnings
