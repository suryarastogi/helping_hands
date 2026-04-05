# v385 — Frontend Component Test Coverage & Backend Docstring Polish

**Status:** Completed
**Created:** 2026-04-05

## Goal

Raise frontend test coverage for three untested/under-tested components above
80% statement coverage, and expand the `Config.from_env()` docstring to meet
Google-style conventions with Args/Returns/Raises sections.

## Context

Backend is at 99.94% coverage (7069 tests). Frontend has 687 tests across 24
test files, but three components have <20% statement coverage:

| Component | Before | Target |
|---|---|---|
| `DiffView.tsx` | 0.56% | >80% |
| `FileExplorer.tsx` | 18.5% | >80% |
| `useOnboarding.ts` | 73.82% | >80% |

`Config.from_env()` is the most complex method in the config module but lacks
Args/Returns/Raises docstring sections.

## Tasks

- [x] Create `DiffView.test.tsx` — test loading/error/empty states, file rendering, diff parsing, collapse toggle, status badges, summary stats
- [x] Create `FileExplorer.test.tsx` — test loading/error/empty states, tree rendering, dir toggle, file selection, filter, changes-only toggle
- [x] Create `useOnboarding.test.tsx` — test idle detection, step navigation, dismiss/restart, localStorage persistence, GitHub token step injection
- [x] Expand `Config.from_env()` docstring with Args/Returns/Raises
- [x] Update INTENT.md, PLANS.md, Week-14 consolidation

## Risks

- FileExplorer's `FileContentViewer` makes fetch calls — needs mocked `fetch`
- useOnboarding uses timers — needs `vi.useFakeTimers()`
