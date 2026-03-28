# v309 — Extract FactoryFloorPanel Component

**Status:** Completed
**Date:** 2026-03-26

## Goal

Extract the Factory Floor HUD panel (~177 lines of inline JSX) from
`HandWorldScene.tsx` into a dedicated `FactoryFloorPanel.tsx` component.
This follows the established component extraction pattern (MonitorCard,
SubmissionForm, ScheduleCard, TaskListSidebar, AppOverlays).

## Motivation

HandWorldScene.tsx is 618 lines with the Factory Floor panel (player name,
color picker, presence list, connection status, emote picker, chat input,
chat history, decoration toolbar) accounting for ~30% of it. Extracting
this panel:

- Reduces HandWorldScene complexity
- Makes multiplayer HUD independently testable
- Follows the established decomposition pattern

## Tasks

- [x] Create `FactoryFloorPanel.tsx` with typed props interface
- [x] Move Factory Floor JSX from HandWorldScene lines 311–488
- [x] Update HandWorldScene to import and render FactoryFloorPanel
- [x] Add FactoryFloorPanel tests (rendering, callbacks, conditional panels)
- [x] Verify all existing tests still pass
- [x] Update docs (FRONTEND.md, INTENT.md)
