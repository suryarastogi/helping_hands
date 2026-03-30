# v335 — Stream Emitter & Multiplayer Coverage + Test Fix

**Status:** completed
**Created:** 2026-03-29

## Goal

Fix the failing `test_env_var_forwarding` test, close testable coverage gaps
in `_StreamJsonEmitter` (claude.py lines 174-175, 184, 206) and
`multiplayer_yjs.py` (lines 287, 292, 339, 342-345), and update docs.

## Tasks

- [x] Fix `test_env_var_forwarding` — clear native CLI auth env vars so ANTHROPIC_API_KEY is forwarded
- [x] Add tests for `_StreamJsonEmitter._process_line` JSON primitive passthrough (line 174-175)
- [x] Add tests for `_StreamJsonEmitter._process_line` non-dict block skip in assistant event (line 184)
- [x] Add tests for `_StreamJsonEmitter._process_line` non-dict block skip in user/tool_result event (line 206)
- [x] Add tests for `get_player_activity_summary` awareness=None continue (line 287)
- [x] Add tests for `get_player_activity_summary` state=None continue (line 292)
- [x] Add tests for `get_decoration_state` ydoc=None continue (line 339)
- [x] Add tests for `get_decoration_state` ydoc.get raises exception (line 342-343)
- [x] Add tests for `get_decoration_state` deco_map=None continue (line 345)
- [x] Run full test suite, verify ≥75% coverage gate
- [x] Update INTENT.md, PLANS.md

## Results

- Fixed `test_env_var_forwarding`: cleared `HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH`
  and `HELPING_HANDS_USE_NATIVE_CLI_AUTH` env vars so native CLI auth doesn't
  block ANTHROPIC_API_KEY forwarding into the Docker sandbox
- 4 new `_StreamJsonEmitter` tests: JSON primitive string, JSON primitive number,
  non-dict block in assistant event, non-dict block in user event
- 5 new `multiplayer_yjs.py` tests: awareness=None skip, unparseable state skip,
  ydoc=None skip, ydoc.get exception skip, deco_map=None skip
- claude.py coverage: 98% → 100% (fully covered)
- multiplayer_yjs.py coverage: 95% → 99% (only import lines 28, 36 remain)
- 6519 backend tests passed, 0 failures, 75.84% coverage ✓
- Docs updated ✓

## Completion criteria

- ClaudeCodeCLIHand claude.py coverage: 98% → 99%+ ✓ (100%)
- multiplayer_yjs.py coverage: 95% → 98%+ ✓ (99%)
- All existing tests still pass ✓ (6519 passed)
- Docs updated ✓
