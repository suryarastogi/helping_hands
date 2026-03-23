# v287: Multiplayer Chat Bubbles

**Date:** 2026-03-23
**Status:** Completed
**Theme:** Multiplayer UX — chat bubbles above player avatars

## Goal

Add text chat to Hand World so players can communicate via speech bubbles
above their avatars. Chat messages are broadcast through the existing Yjs
awareness protocol — no new backend endpoints needed.

## Tasks

- [x] Add `CHAT_DISPLAY_MS` constant to `constants.ts`
- [x] Add `chatMessage` field to Yjs awareness player state in `useMultiplayer`
- [x] Add `sendChat` callback and `localChat`/`remoteChats` state
- [x] Add chat bubble rendering in `PlayerAvatar` component
- [x] Add chat input UI in `HandWorldScene` (Enter to focus, Enter to send)
- [x] Add CSS for `.chat-bubble` with float-up animation
- [x] Add tests for chat broadcast, rendering, and input
- [x] Update design doc and INTENT.md

## Technical Design

**Awareness state extension:**
```json
{
  "player": {
    "player_id": "42",
    "name": "Player 43",
    "color": "#e11d48",
    "x": 50, "y": 50,
    "direction": "down",
    "walking": false,
    "emote": null,
    "chat": null
  }
}
```

**Chat flow:**
1. Player presses Enter (or clicks chat input) → input focuses
2. Types message → Enter to send
3. `sendChat(text)` sets awareness `chat` field
4. After `CHAT_DISPLAY_MS` (4s), clears `chat` to null
5. Remote players see chat bubble above the sender's avatar
6. Local player sees their own chat bubble too

**No backend changes** — awareness protocol already handles arbitrary fields.

## Files Changed

- `frontend/src/constants.ts` — `CHAT_DISPLAY_MS`
- `frontend/src/hooks/useMultiplayer.ts` — chat state + `sendChat`
- `frontend/src/components/PlayerAvatar.tsx` — chat bubble rendering
- `frontend/src/components/HandWorldScene.tsx` — chat input UI
- `frontend/src/styles.css` — `.chat-bubble` styles
- `frontend/src/hooks/useMultiplayer.test.tsx` — chat tests
- `frontend/src/components/PlayerAvatar.test.tsx` — chat bubble tests
- `frontend/src/components/HandWorldScene.test.tsx` — chat input tests
- `docs/design-docs/multiplayer-hand-world.md` — updated
- `INTENT.md` — updated
