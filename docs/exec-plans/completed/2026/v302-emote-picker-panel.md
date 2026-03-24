# v302 — Emote Picker Panel

**Status:** Completed
**Date:** 2026-03-24
**Scope:** Frontend — Hand World multiplayer UX

## Goal

Add a visual emote picker panel to the Hand World HUD so players can discover
and trigger emotes without memorising key bindings (1–4). Currently emotes are
only accessible via keyboard shortcuts with no visual discoverability.

## Changes

### HandWorldScene.tsx
- Add `onTriggerEmote` callback prop
- Add emote picker toggle button in the status hint area
- Render emote picker panel (grid of emoji buttons with names and key hints)
- Clicking an emote calls `onTriggerEmote(key)`

### App.tsx
- Pass `triggerEmote` from `useMultiplayer` as `onTriggerEmote` prop

### styles.css
- `.emote-picker-btn` — toggle button
- `.emote-picker-panel` — floating panel with grid of emote buttons
- `.emote-picker-item` — individual emote button with emoji + label + key hint

### Tests
- HandWorldScene: emote picker toggle, emote click callback, hidden when disconnected
- PlayerAvatar: no changes (tooltips already tested)

### Docs
- FRONTEND.md: document emote picker in HandWorldScene section
- PLANS.md: add v302 entry
- Exec plan: move to completed on success

## Tasks
- [x] Add `onTriggerEmote` callback prop to HandWorldScene
- [x] Implement emote picker toggle button and floating panel UI
- [x] Wire `triggerEmote` from `useMultiplayer` into App.tsx
- [x] Add CSS styles for picker button, panel, and emote items
- [x] Write tests for emote picker toggle, click callback, and disconnect visibility
- [x] Update FRONTEND.md and PLANS.md documentation

## Acceptance Criteria
- [x] Emote picker button visible when connected
- [x] Clicking button toggles panel open/closed
- [x] Panel shows all 4 emotes with emoji, name, and key binding
- [x] Clicking an emote fires `onTriggerEmote` and closes the panel
- [x] Panel hidden when disconnected
- [x] All existing tests still pass (464 total, up from 459)
- [x] New tests cover toggle, click, and visibility (5 new tests)
