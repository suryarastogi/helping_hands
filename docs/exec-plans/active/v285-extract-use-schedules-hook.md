# v285 — Extract useSchedules hook from App.tsx

**Created:** 2026-03-23
**Status:** Complete

## Goal

Extract all schedule-related state and CRUD logic (~200 lines) from `App.tsx`
into a dedicated `useSchedules` hook, continuing the decomposition of the
monolith (2,462 → ~2,260 lines).

## Motivation

- Schedule logic (load, save, delete, toggle, trigger, edit) forms a
  self-contained domain with 7 state variables and 8 handler functions
- Extracting it into `useSchedules` follows the pattern of `useMultiplayer`
- Improves testability — schedule CRUD can be tested in isolation

## Tasks

- [x] **Create `hooks/useSchedules.ts`** — schedule state + CRUD operations
- [x] **Update `App.tsx`** — replace inline schedule state/handlers with hook
- [x] **Add `hooks/useSchedules.test.tsx`** — tests for CRUD operations
- [x] **Update docs** — INTENT.md, FRONTEND.md, PLANS.md, Week-13
- [x] **Verify** — lint, typecheck, all tests pass

## Completion criteria

- `npm --prefix frontend run lint` passes
- `npm --prefix frontend run typecheck` passes
- `npm --prefix frontend run test` passes
- Schedule state and CRUD logic no longer in `App.tsx`
- App.tsx line count reduced by ~200 lines
