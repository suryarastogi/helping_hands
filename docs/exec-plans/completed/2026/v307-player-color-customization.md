# v307: Player Avatar Color Customization

**Date:** 2026-03-26
**Status:** Completed

## Goal

Let players choose their avatar color from the existing PLAYER_COLORS palette
instead of being auto-assigned a color based on Yjs clientID. The chosen color
persists across sessions via localStorage.

## Changes

### `frontend/src/hooks/useMultiplayer.ts`
- Added `loadPlayerColor()` / `savePlayerColor()` localStorage persistence helpers
- Added `playerColor` optional prop to `UseMultiplayerOptions`
- Connection lifecycle uses `playerColor` if provided, falls back to clientID-based
- New effect broadcasts color changes via awareness without reconnecting
  (mirrors the existing name-broadcast pattern)

### `frontend/src/components/HandWorldScene.tsx`
- Imported `PLAYER_COLORS` and `savePlayerColor`
- Added `playerColorInput` and `onPlayerColorChange` props
- Renders a `.color-picker-row` with 10 `.color-swatch` buttons below the
  player name input — click to select, `aria-pressed` for accessibility

### `frontend/src/App.tsx`
- Imported `loadPlayerColor` from useMultiplayer
- Added `playerColorInput` state initialized from localStorage
- Passed `playerColor` to useMultiplayer hook and color props to HandWorldScene

### `frontend/src/styles.css`
- `.color-picker-row` — flex row with 3px gap
- `.color-swatch` — 16px round buttons with hover scale and selected border

## Tasks

- [x] Add `loadPlayerColor()` / `savePlayerColor()` localStorage helpers
- [x] Add `playerColor` optional prop to `UseMultiplayerOptions`
- [x] Broadcast color changes via awareness without reconnecting
- [x] Render color picker swatches in `HandWorldScene`
- [x] Wire color state through `App.tsx`
- [x] Add `.color-picker-row` and `.color-swatch` CSS
- [x] Add 6 tests (3 hook, 3 scene)
