# v281 — Extract WorkerSprite component

**Created:** 2026-03-23
**Status:** Active

## Goal

Extract the ~235-line worker sprite rendering (goose + bot variants) from
`App.tsx` into a dedicated `WorkerSprite` component, and move worker-related
types to `types.ts`.

## Motivation

- The worker sprite JSX (lines 3545-3781) is a self-contained rendering block
  with two variants (goose, bot) totalling ~235 lines — the single largest
  piece of inline markup remaining in App.tsx.
- Extracting it continues the v279-v280 pattern of decomposing the 3,800-line
  monolith into focused, testable components.

## Tasks

- [x] **Move worker types to `types.ts`** — `WorkerVariant`, `CharacterStyle`,
  `SceneWorkerPhase`, `FloatingNumber`.
- [x] **Create `frontend/src/components/WorkerSprite.tsx`** — accepts worker
  data, `isSelected`, `floatingNumbers`, and `onSelect` props. Internal
  `GooseBody` and `BotBody` sub-components for each sprite variant.
- [x] **Update `App.tsx`** — import `WorkerSprite`, remove ~220 lines of inline
  sprite markup. Removed unused `FACTORY_POS`/`INCINERATOR_POS` imports.
- [x] **Add tests** — 12 new WorkerSprite tests (bot/goose rendering, selected
  state, floating numbers, caption, schedule cron, click handler, disabled
  state, position by phase). 245 total (up from 233).
- [x] **Update docs** — `PLANS.md`, `FRONTEND.md`, `INTENT.md`.

## Completion criteria

- `npm --prefix frontend run lint` passes
- `npm --prefix frontend run typecheck` passes
- `npm --prefix frontend run test` passes with ≥233 tests
- Worker sprite markup exists in exactly one place (`WorkerSprite.tsx`)
- No goose/bot body spans remain in `App.tsx`
