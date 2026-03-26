# v308: Multiplayer Hardening — Awareness Validation & Reconnection Resilience

**Date:** 2026-03-26
**Status:** Completed

## Summary

Defensive hardening of the multiplayer system with two main improvements:
server-side awareness state validation and frontend reconnection resilience.

## Server-Side Awareness Validation

### New functions in `multiplayer_yjs.py`:

- **`validate_awareness_state(state)`** — validates and sanitises awareness state
  dicts. Clamps x/y positions to [0, 100], coerces field types, truncates names
  (50 chars max) and chat messages (120 chars max), strips ASCII control chars,
  validates direction enum values. Returns a clean copy without mutating input.

- **`_clamp_float(value, lo, hi)`** — coerces to float and clamps; returns
  midpoint for non-numeric input.

- **`_strip_control_chars(text)`** — removes ASCII 0x00–0x1F except spaces.

- **`get_player_activity_summary()`** — returns active/idle breakdown with
  validated player states (`total`, `active`, `idle`, `players` list).

### Integration:

- `get_connected_players()` now routes through `validate_awareness_state()` for
  hardened position clamping and type safety in the player list API.
- New REST endpoint: `GET /health/multiplayer/activity` in `app.py`.

## Frontend Reconnection Resilience

### Changes to `useMultiplayer.ts`:

- `ConnectionStatus` type extended with `"failed"` terminal state.
- `reconnectAttempts` state counter increments on each `disconnected` event,
  resets to 0 on `connected`.
- After `MAX_RECONNECT_ATTEMPTS` (10) consecutive disconnects, provider is
  disconnected and status transitions to `"failed"`.
- `reconnectAttempts` exposed in hook return value.
- Cleanup (deactivation/unmount) resets attempts to 0.

### Changes to `HandWorldScene.tsx`:

- "Connection failed" banner (`.reconnect-failed`) with red overlay when status
  is `"failed"`.
- Status hint shows "Connection failed" text.
- CSS: `.reconnect-failed` background and `.conn-status-failed` dot color.

## Tests

### Backend (30 new tests):
- `TestValidateAwarenessState`: 16 tests (valid passthrough, position clamping,
  truncation, control char stripping, type coercion, defaults, direction enum)
- `TestClampFloat`: 5 tests (below/above range, in range, non-numeric, None)
- `TestStripControlChars`: 4 tests (null bytes, spaces, tabs/newlines, empty)
- `TestGetPlayerActivitySummary`: 4 tests (empty, counts, position validation,
  exception handling)
- `TestGetConnectedPlayers`: 1 additional test (position clamping in response)
- Total backend multiplayer tests: 54 (up from 24)

### Frontend (7 new tests):
- `useMultiplayer.test.tsx`: 5 reconnection tests (reset on connect, increment
  on disconnect, failed after max attempts, connecting during reconnect, reset
  on deactivate)
- `HandWorldScene.test.tsx`: 2 failed banner tests (banner rendering, status
  hint text)
- 1 updated App.test.tsx test (disconnect → connecting behavior)
- Total frontend tests: 500 (up from 493)

## Files Changed

- `src/helping_hands/server/multiplayer_yjs.py` — validation functions + activity summary
- `src/helping_hands/server/app.py` — new activity endpoint + import
- `frontend/src/constants.ts` — `MAX_RECONNECT_ATTEMPTS`
- `frontend/src/hooks/useMultiplayer.ts` — reconnection tracking + "failed" state
- `frontend/src/components/HandWorldScene.tsx` — failed banner + status text
- `frontend/src/styles.css` — failed state CSS
- `tests/test_multiplayer_yjs.py` — 30 new tests
- `frontend/src/hooks/useMultiplayer.test.tsx` — 5 new tests
- `frontend/src/components/HandWorldScene.test.tsx` — 2 new tests
- `frontend/src/App.test.tsx` — 1 updated test
