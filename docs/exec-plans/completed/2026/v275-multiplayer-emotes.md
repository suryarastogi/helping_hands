# v275: Multiplayer Emotes

**Status:** Completed
**Created:** 2026-03-23
**Intent:** Add emote animations to multiplayer Hand World

## Goal

Allow players to trigger emote animations (wave, celebrate, thumbs-up, sparkle) that appear above their avatar and are broadcast to all other connected players. This is the next self-contained enhancement from the multiplayer design doc's "Future extensions" list.

## Tasks

### Phase 1: Backend — Emote Message Type
- [ ] Add `emote` message type to `world_websocket_endpoint` handler
- [ ] Add `_VALID_EMOTES` constant for allowed emote names
- [ ] Broadcast `player_emoted` message to all other players
- [ ] Validate emote name server-side

### Phase 2: Frontend — Emote UI & Key Bindings
- [ ] Add `EmoteType` and emote state to RemotePlayer type
- [ ] Add key bindings (1–4) to trigger emotes
- [ ] Render emote bubble above local and remote player avatars
- [ ] Auto-dismiss emote after animation duration
- [ ] Add CSS for emote bubble animation (float up + fade out)

### Phase 3: Testing
- [ ] Backend: emote broadcast, invalid emote rejection
- [ ] Frontend: emote key binding, emote rendering, auto-dismiss

### Phase 4: Documentation
- [ ] Update multiplayer design doc with emote protocol
- [ ] Update FRONTEND.md with emote details

## Protocol Extension

```
Client → Server (JSON):
  { "type": "emote", "emote": "wave" }

Server → Client (JSON):
  { "type": "player_emoted", "player_id": "abc123", "emote": "wave" }
```

## Emote Set

| Key | Emote | Emoji |
|-----|-------|-------|
| 1   | wave  | 👋    |
| 2   | celebrate | 🎉 |
| 3   | thumbsup | 👍  |
| 4   | sparkle | ✨   |

## Dependencies
- No new packages required
