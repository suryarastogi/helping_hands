# v324 — Branch Coverage Hardening: useMultiplayer, useSceneWorkers, HandWorldScene, App

## Goal

Raise frontend branch coverage from 90.47% toward 92%+ by targeting the files with
the lowest branch percentages: `useMultiplayer.ts` (81.09%), `WorkerSprite.tsx`
(84.61%), `App.tsx` (81.25%), `useSceneWorkers.ts` (93.33%), and
`HandWorldScene.tsx` (97.5%).

## Uncovered branches identified

| File | Branch % | Uncovered lines | Branch description |
|---|---|---|---|
| `useMultiplayer.ts` | 81.09% | 528-531 | Position broadcast: clear existing timer when elapsed ≥ interval |
| `useMultiplayer.ts` | 81.09% | 757-759 | Cursor broadcast: clear existing timer when elapsed ≥ interval |
| `useSceneWorkers.ts` | 93.33% | 104-105 | Fallback to `DEFAULT_CHARACTER_STYLE` when provider not in defaults map |
| `useSceneWorkers.ts` | 93.33% | 174-176 | Existing worker already in exit phase when task goes inactive |
| `HandWorldScene.tsx` | 97.5% | 158-165 | Double-click decoration placement guard branches |
| `App.tsx` | 81.25% | 178-180 | taskError memo: non-string error, missing error_type |
| `WorkerSprite.tsx` | 84.61% | 109 | cronFrequency returns null for schedule |

## Plan

- [ ] Add useMultiplayer tests for position broadcast timer clearing edge case
- [ ] Add useMultiplayer tests for cursor broadcast timer clearing edge case
- [ ] Add useSceneWorkers tests for fallback character style and exit-phase worker
- [ ] Add HandWorldScene tests for double-click decoration placement
- [ ] Add App.tsx tests for taskError memo branches
- [ ] Add WorkerSprite test for null cronFrequency
- [ ] Run tests, verify coverage improvement
- [ ] Update docs (INTENT.md, daily consolidation)
