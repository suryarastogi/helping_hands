# v283 — Extract HandWorldScene component

**Created:** 2026-03-23
**Status:** Complete

## Goal

Extract the Hand World scene rendering (~250 lines of JSX) from `App.tsx`
into a dedicated `HandWorldScene` component. This continues the
decomposition of the monolith (2,691 → 2,462 lines).

## Motivation

- The world scene (lines 2409-2656) is a self-contained visual block
  rendering the zen garden, factory, desks, players, and workers.
- Extracting it improves readability and makes the multiplayer view
  independently testable.
- Follows the same pattern as `PlayerAvatar` (v280) and `WorkerSprite` (v281).

## Tasks

- [x] **Create `components/HandWorldScene.tsx`** — accepts props for scene
  state (deskSlots, workerEntries, player state, multiplayer state,
  Claude usage, floating numbers) and renders the full world scene.
- [x] **Update `App.tsx`** — replace inline scene JSX with `<HandWorldScene />`.
  Removed unused `PlayerAvatar`, `WorkerSprite`, `savePlayerName` imports.
- [x] **Add tests** — 15 render tests for HandWorldScene covering scene
  structure, decorations, factory/incinerator, desk rendering, player
  avatars, worker sprites, HUD panels, presence, connection status,
  Claude usage, and name input callback.
- [x] **Update docs** — INTENT.md, FRONTEND.md, PLANS.md.

## Completion criteria

- `npm --prefix frontend run lint` passes ✓
- `npm --prefix frontend run typecheck` passes ✓
- `npm --prefix frontend run test` passes with 260 tests (up from 245) ✓
- World scene JSX no longer in `App.tsx` ✓
- App.tsx reduced from 2,691 to 2,462 lines (-229) ✓
