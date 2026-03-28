# v324 — Remote Player CSS Fixes & Initial Position Sync

**Date:** 2026-03-27
**Status:** Completed
**Intent:** Multiplayer Hand World polish — fix CSS rendering bugs and position sync

## Context

The multiplayer Hand World system (Yjs + y-websocket) is mature with 717+ frontend
tests and 90+ backend tests. During review, three bugs were identified:

1. **Duplicate CSS `transition` on `.remote-player`** — two declarations, second
   (80ms) silently overrides first (150ms). Consolidate to one.
2. **`pointer-events: none` on `.remote-player`** — prevents tooltip hover from
   working in real browsers (unit tests pass because `fireEvent` bypasses CSS).
   Should be `auto` so tooltips function as designed in v301.
3. **Initial awareness position hardcoded to (50, 50)** — `useMultiplayer` sets
   initial Yjs awareness position to center instead of the actual random spawn
   from `useMovement`. Remote players briefly see the wrong initial position.

## Tasks

- [x] Fix duplicate `transition` in styles.css
- [x] Fix `pointer-events` on `.remote-player`
- [x] Use `playerPosition` for initial awareness state in `useMultiplayer`
- [x] Add tests for initial position sync
- [x] Update INTENT.md, PLANS.md, design doc

## Outcome

- CSS: single transition declaration, pointer-events restored for tooltips
- useMultiplayer: initial awareness position matches actual spawn
- Tests: verify initial broadcast uses spawn position
