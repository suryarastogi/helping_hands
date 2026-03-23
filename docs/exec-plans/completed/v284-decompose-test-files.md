# v284 — Decompose test files to match component structure

**Created:** 2026-03-23
**Status:** Complete

## Goal

Split the monolithic `App.test.tsx` (2,395 lines, 260 tests) into per-module
test files matching the component/hook extraction done in v280–v283. App-level
integration tests stay in `App.test.tsx`; extracted module tests move next to
their source files.

## Motivation

- App.test.tsx has grown alongside the component extractions but tests for
  extracted modules still live in the monolith
- Co-locating tests with source improves discoverability and makes it easier
  to run tests for a single module (`vitest run src/components/PlayerAvatar.test.tsx`)
- Aligns with the frontend decomposition pattern established in v280–v283

## Tasks

- [x] **Create `components/PlayerAvatar.test.tsx`** — 6 tests for PlayerAvatar
- [x] **Create `components/WorkerSprite.test.tsx`** — 12 tests for WorkerSprite
- [x] **Create `components/HandWorldScene.test.tsx`** — 15 tests for HandWorldScene
- [x] **Create `hooks/useMultiplayer.test.tsx`** — 7 tests (loadPlayerName/savePlayerName + hook tests)
- [x] **Create `constants.test.ts`** — 5 tests for constants module
- [x] **Remove extracted tests from `App.test.tsx`** — keep Yjs Multiplayer Awareness
  and all App-level describe blocks
- [x] **Update docs** — INTENT.md, FRONTEND.md, PLANS.md
- [x] **Verify** — all 260 tests pass, lint clean, typecheck clean

## Completion criteria

- `npm --prefix frontend run test` passes with 260 tests
- `npm --prefix frontend run lint` passes
- `npm --prefix frontend run typecheck` passes
- Each extracted component/hook has a co-located test file
- App.test.tsx contains only App-level integration tests + Yjs awareness tests
