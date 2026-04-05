# v377 — Model Provider & Config Validation Hardening

**Status:** ✅ Complete
**Date:** 2026-04-05

## Goal

Harden input validation in model provider resolution, AI provider completion,
and config loading to prevent silent failures from malformed inputs.

## Tasks

- [x] Add `.strip()` on provider name in `resolve_hand_model()`
- [x] Emit warning on unknown explicit provider
- [x] Use `require_non_empty_string` in `AIProvider.complete()`
- [x] Add type guards on `provider.name` in build functions
- [x] Harden `Config.from_env()` enabled_tools type coercion
- [x] Add 19 tests covering all changes

## Changes

### 1. Provider name `strip()` in `resolve_hand_model()` (`model_provider.py`)

Added `.strip()` on `maybe_provider` before PROVIDERS dict lookup so that
`" anthropic /model"` matches correctly instead of silently falling through
to inference.

### 2. Warning on unknown explicit provider (`model_provider.py`)

When `provider/model` format specifies an unrecognized provider, a
`logger.warning()` is now emitted before falling through to inference.
Previously this was completely silent, making it hard to debug typos like
`"anthrpic/claude-opus"`.

### 3. Unified `require_non_empty_string` in `AIProvider.complete()` (`types.py`)

Replaced inline `not resolved_model or not resolved_model.strip()` check
with the shared `require_non_empty_string()` helper, matching the pattern
used in `build_langchain_chat_model()` and `build_atomic_client()`.
Original error message preserved via catch-and-re-raise.

### 4. Type guards on `provider.name` in build functions (`model_provider.py`)

Added `require_non_empty_string(hand_model.provider.name, ...)` at the top
of both `build_langchain_chat_model()` and `build_atomic_client()`. Catches
empty or non-string provider names early with a clear error instead of
falling through to the unsupported-provider RuntimeError.

### 5. Config `enabled_tools` type coercion hardening (`config.py`)

Added explicit `isinstance` check for expected types (`str`, `tuple`, `list`,
`None`) in `Config.from_env()`. Unexpected types (e.g. `int`, `dict`) now
log a warning and default to empty tuple instead of being passed through
to `normalize_tool_selection()` which would raise an opaque error.

## Tests

19 new tests in `tests/test_v377_model_provider_and_config_hardening.py`:

- **Provider strip** (1): whitespace-tolerant provider name matching
- **Unknown provider warning** (3): warning logged, model still resolves, no warning for known
- **AIProvider.complete validation** (5): None/empty/whitespace model, valid model, default model
- **Build function type guards** (4): empty/None provider.name for both langchain and atomic
- **Config enabled_tools** (6): bool, string, tuple, unexpected int, unexpected dict, None

**7016 total tests pass. 99.93% coverage.**
