# v289 — Chat History Panel

**Date:** 2026-03-23
**Status:** Completed
**Scope:** Frontend multiplayer UX improvement

## Goal

Add a scrollable chat history panel to Hand World so players can see past
messages from all participants. Currently chat bubbles appear above avatars for
4 seconds and disappear — there is no way to review earlier messages.

## Changes

### 1. Types (`types.ts`)
- Add `ChatMessage` type: `{ id: string; playerName: string; playerColor: string; text: string; timestamp: number }`

### 2. Constants (`constants.ts`)
- Add `CHAT_HISTORY_MAX = 50` — maximum messages retained in history

### 3. Hook (`useMultiplayer.ts`)
- Add `chatHistory: ChatMessage[]` state
- Capture local chat messages in `sendChat()`
- Capture remote chat messages from awareness change events
- Deduplicate by message id (timestamp + clientId)
- Expose `chatHistory` in return value

### 4. Scene (`HandWorldScene.tsx`)
- Add `chatHistory` prop
- Render a collapsible chat history panel below the chat input
- Auto-scroll to newest message
- Show player name (colored) + message text + relative timestamp

### 5. CSS (`styles.css`)
- Style `.chat-history-panel`, `.chat-history-message`, `.chat-history-name`

### 6. Tests
- `useMultiplayer.test.tsx` — verify chatHistory accumulates on local send + remote awareness
- `HandWorldScene.test.tsx` — verify chat history panel renders messages

### 7. Documentation
- Update `docs/design-docs/multiplayer-hand-world.md` with chat history section

## Metrics
- Target: >80% branch coverage maintained
- New tests: ~6-8
