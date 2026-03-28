# v298: Multiplayer Smooth Movement & Typing Indicator

**Status:** Completed

## Goal

Two self-contained multiplayer UX improvements:
1. **Smooth remote player movement** — CSS transitions so remote avatars glide instead of snapping
2. **Typing indicator** — Show a "..." bubble above remote players who are typing in chat

## Tasks

- [x] Add CSS transition to remote-player positioning for smooth interpolation
- [x] Add typing indicator broadcast via Yjs awareness
- [x] Render typing indicator bubble in PlayerAvatar
- [x] Add tests for smooth movement (CSS transition class) and typing indicator
- [x] Update design doc and FRONTEND.md
- [x] Run full test suite — verify all pass

## Technical Approach

### Smooth remote movement
- Add `transition: left 150ms linear, top 150ms linear` to `.remote-player` CSS
- This gives ~9fps interpolation between awareness updates (awareness fires ~6-10Hz)
- No JS changes needed — pure CSS improvement

### Typing indicator
- Frontend: track `typing: boolean` in Yjs awareness state
- Set `typing: true` when chat input has focus and non-empty text
- Set `typing: false` on blur, empty text, or message send
- Render a "..." bubble in PlayerAvatar when `typing && !emote && !chat`
- CSS animation: ellipsis pulse/bounce

## Test Plan
- Remote player CSS transition class assertion
- Typing indicator renders when `typing` prop is true
- Typing indicator suppressed when emote/chat active
- Typing state broadcast via awareness
