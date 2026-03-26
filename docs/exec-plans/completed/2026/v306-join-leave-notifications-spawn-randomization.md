# v306: Join/Leave Notifications & Spawn Randomization

**Status:** Completed
**Created:** 2026-03-26

## Goal

Improve the multiplayer Hand World experience with two self-contained
enhancements:

1. **Join/leave notifications** — When a player connects or disconnects, a
   system message appears in the chat history panel (e.g. "Player 42 joined"
   / "Player 42 left"). This gives presence awareness beyond the sidebar.

2. **Randomized spawn positions** — Instead of all players spawning at the
   center (50, 50), each player starts at a random position within the
   walkable area. This prevents avatar overlap on initial load.

## Approach

### Join/leave detection

The Yjs awareness `change` event fires with `{added, updated, removed}`
client ID arrays. We can use `added` and `removed` to detect joins/leaves
and inject system messages into the chat history.

- Add optional `isSystem: boolean` field to `ChatMessage` type
- On `added` client IDs in awareness change, record a "joined" system message
- On `removed` client IDs, record a "left" system message
- Filter out the local client ID from join/leave messages
- System messages rendered with distinct styling (italic, muted color)

### Spawn randomization

- `useMovement` initial position randomized within `OFFICE_BOUNDS` with
  padding to avoid edge spawns
- Uses a stable random position computed once per mount

## Files changed

- `frontend/src/types.ts` — `ChatMessage.isSystem` optional field
- `frontend/src/constants.ts` — `SYSTEM_MESSAGE_COLOR` constant
- `frontend/src/hooks/useMultiplayer.ts` — join/leave detection via awareness `change` event
- `frontend/src/hooks/useMovement.ts` — randomized initial spawn position
- `frontend/src/components/HandWorldScene.tsx` — system message styling in chat history
- `frontend/src/styles.css` — `.chat-history-system` styling
- Tests for all changes

## Tasks

- [x] Add `isSystem` optional field to `ChatMessage` type
- [x] Add `SYSTEM_MESSAGE_COLOR` constant
- [x] Detect join/leave via awareness `change` event in `useMultiplayer`
- [x] Randomize initial spawn position in `useMovement`
- [x] Style system messages in `HandWorldScene` chat history
- [x] Add `.chat-history-system` CSS styling
- [x] Add tests for all changes

## Out of scope

- Sound effects for join/leave
- Private messaging
- Player collision avoidance
