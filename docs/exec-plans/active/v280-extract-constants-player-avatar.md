# v280 — Extract constants module & PlayerAvatar component

**Created:** 2026-03-23
**Status:** Active

## Goal

Decouple multiplayer constants from the monolithic `App.tsx` and deduplicate
the player avatar markup that is copy-pasted between local and remote players.

## Motivation

- `useMultiplayer.ts` imports `EMOTE_DISPLAY_MS`, `EMOTE_KEY_BINDINGS`, and
  `PLAYER_COLORS` directly from `App.tsx` — tight coupling to a 3,800-line
  file that should only export the root component.
- The human-body `<span>` tree (helmet, visor, torso, arms, legs, boots) is
  rendered verbatim in **two** places: the local player div and the
  `remotePlayers.map()` loop.  Any sprite change must be duplicated.

## Tasks

- [x] **Create `frontend/src/constants.ts`** — move `EMOTE_DISPLAY_MS`,
  `EMOTE_MAP`, `EMOTE_KEY_BINDINGS`, `PLAYER_COLORS`, `PLAYER_MOVE_STEP`,
  `PLAYER_SIZE`, `DESK_SIZE`, `FACTORY_POS`, `INCINERATOR_POS`,
  `FACTORY_COLLISION`, `INCINERATOR_COLLISION`, `OFFICE_BOUNDS` out of
  `App.tsx`.
- [x] **Create `frontend/src/components/PlayerAvatar.tsx`** — shared component
  for the human-body sprite tree, accepting `direction`, `walking`, `name`,
  `emote`, `color`, and `isLocal` props.
- [x] **Update `App.tsx`** — import constants from `constants.ts`, use
  `<PlayerAvatar>` for both local and remote players.
- [x] **Update `useMultiplayer.ts`** — import from `constants.ts` instead of
  `App.tsx`.
- [x] **Add tests** for `PlayerAvatar` rendering and constants exports.
- [x] **Update docs** — `PLANS.md`, `INTENT.md`, `FRONTEND.md`.

## Completion criteria

- `npm --prefix frontend run lint` passes
- `npm --prefix frontend run typecheck` passes
- `npm --prefix frontend run test` passes with ≥222 tests
- No `App.tsx` imports in `useMultiplayer.ts`
- Player body markup exists in exactly one place
