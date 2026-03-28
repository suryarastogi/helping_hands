# v315 — Multiplayer Cursor Sharing

**Status:** Completed
**Date:** 2026-03-27

## Goal

Add real-time mouse cursor sharing to Hand World so players can see each
other's cursor positions in the scene. This is a natural extension of the Yjs
awareness-based multiplayer system and a common collaborative-editing UX
pattern.

## Tasks

- [x] Add `CursorPosition` type to `types.ts`
- [x] Add `CURSOR_BROADCAST_INTERVAL_MS` constant
- [x] Extend `useMultiplayer` hook: broadcast cursor via awareness, expose
      `remoteCursors` and `updateCursor` in return value
- [x] Extend `HandWorldScene`: pass cursor props, add `onMouseMove` / `onMouseLeave`
      handlers, render `RemoteCursor` components
- [x] Create `RemoteCursor` component (colored arrow + name label)
- [x] Add CSS for `.remote-cursor`
- [x] Add tests (hook cursor broadcast, scene cursor rendering)
- [x] Update docs (INTENT.md, design doc, daily plan)

## Approach

- Cursor position is ephemeral — broadcast via Yjs awareness (same as player
  position, emotes, chat), not via Y.Map.
- Throttle cursor broadcasts to `CURSOR_BROADCAST_INTERVAL_MS` (100ms) to
  avoid saturating the network.
- When the mouse leaves the scene, set cursor to `null` so remote clients
  hide the cursor dot.
- Render as a small colored arrow pointer with the player's name next to it.
