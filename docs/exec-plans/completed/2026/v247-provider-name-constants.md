# v247 — Extract provider name constants in model_provider.py

**Status:** Completed
**Date:** 2026-03-17

## Problem

`model_provider.py` used 12 bare string literals (`"openai"`, `"anthropic"`,
`"google"`, `"ollama"`, `"litellm"`) across `_infer_provider_name()`,
`build_langchain_chat_model()`, and `build_atomic_client()`. `goose.py` had
8 more across `_GOOSE_DEFAULT_PROVIDER`, `_describe_auth()`,
`_normalize_goose_provider()`, `_infer_goose_provider_from_model()`, and
`_build_subprocess_env()`. A typo in any would silently break provider routing.

## Tasks

- [x] Create this plan
- [x] Add `_PROVIDER_*` constants to `model_provider.py`
- [x] Replace 12 bare strings in `model_provider.py` with constants
- [x] Replace 8 bare strings in `goose.py` with constants
- [x] Export constants in `__all__`
- [x] Add AST-based test: no bare provider name strings remain in source
- [x] Add behavioral tests for constant values and provider resolution
- [x] Update existing `__all__` tests for new export count
- [x] Run full test suite + lint

## Completion criteria

- Zero bare provider name strings in `model_provider.py` and `goose.py`
- AST-based regression test prevents reintroduction
- All new tests pass
- Full test suite passes with no regressions
- Lint and format checks clean

## Changes

### `src/helping_hands/lib/hands/v1/hand/model_provider.py`
- Added 5 constants: `_PROVIDER_OPENAI`, `_PROVIDER_ANTHROPIC`,
  `_PROVIDER_GOOGLE`, `_PROVIDER_OLLAMA`, `_PROVIDER_LITELLM`
- Replaced 12 bare string literals with constants across
  `resolve_hand_model()`, `_infer_provider_name()`,
  `build_langchain_chat_model()`, `build_atomic_client()`
- Added constants to `__all__` (4 → 9 entries)

### `src/helping_hands/lib/hands/v1/hand/cli/goose.py`
- Imported `_PROVIDER_ANTHROPIC`, `_PROVIDER_GOOGLE`, `_PROVIDER_OLLAMA`,
  `_PROVIDER_OPENAI` from `model_provider`
- Replaced 8 bare string literals with constants across
  `_GOOSE_DEFAULT_PROVIDER`, `_pr_description_cmd()`, `_describe_auth()`,
  `_normalize_goose_provider()`, `_infer_goose_provider_from_model()`,
  `_build_subprocess_env()`

### `tests/test_v247_provider_name_constants.py` (new)
- 24 tests across 6 test classes
- Constant values, types, distinctness, lowercase, non-empty
- `__all__` export verification
- AST-based source checks for both model_provider.py and goose.py
- Behavioral tests for provider resolution (default, prefix inference,
  explicit provider/model, registry consistency)

### `tests/test_v159_all_exports.py`
- Updated `TestModelProviderAllExport` to allow `_PROVIDER_*` private names
  in `__all__` and expect count of 9

## Test results

- **24 new tests** (0 skipped)
- **5855 passed**, 249 skipped, 0 failures
- All lint/format checks pass
