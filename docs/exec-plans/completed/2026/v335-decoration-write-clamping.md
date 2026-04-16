# v335 — Decoration Placement Validation & Y.Map Read Hardening

**Status:** completed
**Created:** 2026-04-17
**Completed:** 2026-04-17

## Goal

Mirror the v320 backend/cursor hardening for the shared world decoration
feature. Today `placeDecoration()` writes raw click-relative x/y coords and
arbitrary-length emoji strings to the shared Y.Map, which is broadcast to all
peers. The backend `get_decoration_state()` endpoint clamps on read, but peer
browsers render whatever the Y.Map holds. A buggy client could push
out-of-range coords or an overly long emoji field.

## Tasks

- [x] Add `DECO_EMOJI_MAX_LENGTH` constant in `constants.ts`
- [x] Clamp x/y and truncate/trim emoji in `placeDecoration()` before writing
      to Y.Map
- [x] Normalize x/y and emoji length in the `syncDecorations()` Y.Map observer
      callback so peer-produced invalid state is sanitized on display
- [x] Add 8 frontend tests covering clamp + trim + truncate + non-finite
      defaults + peer-produced sync-time normalization
- [x] Update FRONTEND.md with the new constant
- [x] Move plan to completed, update INTENT.md and PLANS.md

## Results

- Added `DECO_EMOJI_MAX_LENGTH = 8` constant in `frontend/src/constants.ts`
- `placeDecoration()` now: trims emoji → skips if empty → slices to
  `DECO_EMOJI_MAX_LENGTH`; clamps finite x/y to `[0, 100]` and falls back to
  50 for non-finite (NaN/Infinity)
- `syncDecorations()` observer rejects non-string/empty emojis, truncates
  long emojis, and clamps x/y so peer-produced invalid state is sanitized
  before it reaches React state
- 8 new tests in `useMultiplayer.test.tsx` (clamp x below 0, clamp x/y above
  100, skip empty/whitespace emoji, truncate long emoji, non-finite → 50,
  peer-set out-of-range clamp, peer-set long emoji truncation, peer-set
  missing/non-string emoji drop)
- 744 frontend tests pass (up from 732), lint + typecheck clean

## Completion criteria

- `placeDecoration(emoji, x, y)` never writes x/y outside [0, 100] ✓
- `placeDecoration` skips when trimmed emoji is empty ✓
- Emoji stored in Y.Map never exceeds `DECO_EMOJI_MAX_LENGTH` ✓
- `decorations` state surfaces clamped x/y even if a peer sent out-of-range ✓
- All existing frontend tests still pass ✓ (744/744)
