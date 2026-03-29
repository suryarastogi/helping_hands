# v337 — Multiplayer YJS & Claude Stream Emitter Coverage

**Status:** completed
**Created:** 2026-03-29

## Goal

Close remaining testable coverage gaps in `multiplayer_yjs.py` (95% → ~99%) and
`cli/claude.py` (98% → ~99%). Target the specific uncovered branches: decoration
state reading (ydoc None, deco_map exception, deco_map None), activity summary
(awareness None, unparseable state), and stream emitter non-dict event/block handling.

## Tasks

- [x] Move v336 from active to completed, update PLANS.md
- [x] Add `get_player_activity_summary` tests: awareness-is-None room, unparseable raw state
- [x] Add `get_decoration_state` tests: ydoc-is-None room, deco_map raises, deco_map-is-None
- [x] Add `_StreamJsonEmitter` tests: non-dict JSON event (primitive), non-dict block in assistant/user message
- [x] Run full test suite, verify ≥75% coverage and 0 failures
- [x] Update INTENT.md, PLANS.md, Week-13

## Results

- **multiplayer_yjs.py (95% → 99%):** 5 new tests — `get_player_activity_summary`
  awareness-None room skip, unparseable raw state skip; `get_decoration_state`
  ydoc-None room skip, deco_map exception skip, deco_map-None skip
- **cli/claude.py (98% → 99%):** 4 new tests — JSON primitive string/number
  pass-through, non-dict block in assistant message skipped, non-dict block in
  user message skipped
- Only uncovered lines remaining: import-level `_HAS_PYCRDT = True` (lines 28, 36)
  which depend on runtime package availability
- 6533 backend tests passed, 0 failures, 75.84% coverage ✓
- Docs updated ✓

## Completion criteria

- All uncovered branches in multiplayer_yjs.py lines 287, 292, 339, 342-343, 345 covered ✓
- All uncovered branches in cli/claude.py lines 174-175, 184, 206 covered ✓
- All existing tests still pass ✓ (6533 passed)
- Docs updated ✓
