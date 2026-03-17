# v267 — DRY CLI Label Prefix Pattern

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

`_TwoPhaseCLIHand` in `cli/base.py` uses the pattern `f"[{self._CLI_LABEL}] ..."` 32 times
to prefix log/status messages with the backend label. This is repetitive and error-prone.

## Tasks

- [x] Add `_label_msg(msg: str) -> str` helper method to `_TwoPhaseCLIHand`
- [x] Replace all 32 occurrences of inline `f"[{self._CLI_LABEL}] ..."` with `self._label_msg(...)`
- [x] Add 7 unit tests for `_label_msg()` in `test_cli_hand_base_helpers.py`
- [x] Run full test suite — 6220 passed, 272 skipped
- [x] Ruff lint + format clean

## Completion criteria

- [x] `_label_msg()` method exists on `_TwoPhaseCLIHand`
- [x] Zero remaining `f"[{self._CLI_LABEL}]` patterns outside `_label_msg` itself
- [x] All tests pass, ruff clean

## Changes

- `src/helping_hands/lib/hands/v1/hand/cli/base.py` — added `_label_msg()`, replaced 32 inline patterns
- `tests/test_cli_hand_base_helpers.py` — 7 new tests in `TestLabelMsg` class

## Test results

- 6220 passed, 272 skipped (7 net new tests)
