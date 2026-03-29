# v335 — ModelProvider Coverage Hardening

**Status:** completed
**Created:** 2026-03-29

## Goal

Close remaining coverage gaps in `model_provider.py` by adding dedicated unit
tests for `_require_langchain_class` and untested branches in
`resolve_hand_model`, `build_langchain_chat_model`, and `build_atomic_client`.
Also fix pre-existing `test_env_var_forwarding` failure caused by env
variable leaking into test environment.

## Tasks

- [x] Add direct `_require_langchain_class` tests: success, failure with derived install, failure with custom install
- [x] Add `resolve_hand_model` tests for all direct provider names (openai, anthropic, google, litellm)
- [x] Add `resolve_hand_model` tests for `provider/` trailing-slash with empty model for non-ollama providers
- [x] Add `build_langchain_chat_model` empty model validation test
- [x] Add `build_atomic_client` empty model validation test
- [x] Fix `test_env_var_forwarding` — clear `HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH` env var
- [x] Run full test suite, verify ≥75% coverage gate
- [x] Update INTENT.md, PLANS.md

## Results

- 15 new model_provider tests (51 total, up from 36): 3 `_require_langchain_class`,
  4 direct provider names, 5 provider trailing-slash, 1 whitespace model,
  2 empty model validation
- Fixed pre-existing `test_env_var_forwarding` env leak
- 6524 backend tests passed, 0 failures, 75.64% coverage ✓
- Docs updated ✓

## Completion criteria

- model_provider.py coverage ≥ 99% ✓ (100%)
- All existing tests still pass ✓ (6524 passed)
- Docs updated ✓
