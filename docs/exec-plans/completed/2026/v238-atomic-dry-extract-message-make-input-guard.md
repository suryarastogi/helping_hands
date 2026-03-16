# v238 — AtomicHand DRY _extract_message, _make_input None guard tests

**Status:** completed
**Created:** 2026-03-16
**Completed:** 2026-03-16

## Motivation

`AtomicHand` (atomic.py) had 3 inline `hasattr(partial, "chat_message")` checks
plus 1 direct `.chat_message` access in `run()`, duplicating the pattern already
encapsulated by `BasicAtomicHand._extract_message()` in iterative.py.
Additionally, the `_make_input()` `_input_schema is None` guard was untested on
both Atomic hand classes.

## Changes

### Code changes

- **Added `_extract_message()` static method to `AtomicHand`** — returns `""` for
  no/falsy `chat_message` (matching the single-shot stream pattern where only real
  content should be yielded, unlike `BasicAtomicHand` which falls back to `str(response)`
  for delta tracking)
- **Replaced 3 inline `hasattr(partial, "chat_message")` patterns** in `stream()` with
  `self._extract_message(partial)`
- **Changed `run()` to use `_extract_message()`** instead of direct `.chat_message` access

### Tasks completed

- [x] Add `_extract_message()` static method to `AtomicHand`
- [x] Replace 3 inline `hasattr(partial, "chat_message")` patterns in `atomic.py`
- [x] Replace direct `.chat_message` access in `run()` with `_extract_message()`
- [x] Test `_extract_message()` on `AtomicHand` (6 tests: truthy, no attr, empty, None, plain string, numeric)
- [x] Test `_make_input()` None guard on both `AtomicHand` and `BasicAtomicHand` (2 tests)
- [x] Test `run()` delegates to `_extract_message` (2 tests)
- [x] Test `stream()` uses `_extract_message` across all paths (4 tests)
- [x] Test consistency between `AtomicHand` and `BasicAtomicHand` `_extract_message` (3 tests)
- [x] Update PLANS.md

### Tasks skipped

- CLI `except Exception` narrowing (cli/main.py:380) — skipped because the handler
  catches errors from external AI provider libraries (openai, anthropic, google SDK,
  litellm, atomic-agents) whose exception types can't be easily narrowed without
  importing all provider packages. The handler re-raises for non-matching exceptions,
  so the broad catch is acceptable at this top-level entry point.

## Test results

- 17 new tests added
- 5678 passed, 225 skipped
- Coverage: 78.55%
