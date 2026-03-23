# v286 — Extract useMovement hook from App.tsx

**Created:** 2026-03-23
**Status:** Complete

## Goal

Extract all player movement logic (~95 lines) from `App.tsx` into a dedicated
`useMovement` hook, continuing the decomposition of the monolith (2,275 → ~2,180 lines).

## Motivation

- Movement logic (keyboard input, position clamping, collision detection, direction
  tracking) forms a self-contained domain with 3 state variables and 2 effects
- Extracting it into `useMovement` follows the pattern of `useMultiplayer` and
  `useSchedules`
- Improves testability — movement, collision, and keyboard binding can be tested
  in isolation without rendering the full App

## Tasks

- [x] **Create `hooks/useMovement.ts`** — player position, direction, walking state, keyboard handling
- [x] **Update `App.tsx`** — replace inline movement state/effects with hook
- [x] **Add `hooks/useMovement.test.tsx`** — tests for movement, collision, keyboard
- [x] **Fix stale docs** — FRONTEND.md legacy `/ws/world` reference, update component tree
- [x] **Update docs** — INTENT.md, Week-13, daily consolidation
- [x] **Verify** — lint, typecheck, all tests pass

## Completion criteria

- `npm --prefix frontend run lint` passes
- `npm --prefix frontend run typecheck` passes
- `npm --prefix frontend run test` passes
- Movement state and keyboard handling no longer in `App.tsx`
- App.tsx line count reduced by ~95 lines
