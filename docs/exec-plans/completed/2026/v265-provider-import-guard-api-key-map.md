# v265: Extract provider import guard and shared API key env map

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Goal

Two self-contained DRY improvements in the AI provider and CLI hand layers:

1. **Provider import guard** — All 5 AI provider `_build_inner()` methods have
   identical `try: import X except ImportError: raise RuntimeError(...)` blocks.
   Extract a `_require_sdk()` helper method on the `AIProvider` base class that
   takes a module name and returns the imported module, raising `RuntimeError`
   with the `install_hint` on failure.

2. **Shared provider-to-API-key env var mapping** — `goose.py` (line 63–67) and
   `opencode.py` (line 13–18) both define identical `{provider: env_var}` dicts
   mapping provider names to their API key environment variables. Extract this as
   `PROVIDER_API_KEY_ENV` constant in `model_provider.py` (where `_PROVIDER_*`
   constants already live) and import it in both consumers.

## Tasks

- [x] Create active plan
- [x] Add `_require_sdk()` method to `AIProvider` base class in `types.py`
- [x] Refactor 5 provider `_build_inner()` methods to use `_require_sdk()`
- [x] Add `PROVIDER_API_KEY_ENV` constant in `model_provider.py`
- [x] Update `goose.py` and `opencode.py` to import shared mapping
- [x] Add tests for all changes
- [x] Run lint, type check, tests
- [x] Update docs, move plan to completed

## Completion criteria

- No duplicate ImportError blocks in AI provider classes
- No duplicate provider-to-env-var dicts in CLI hands
- All 6206 tests pass, 272 skipped, 79% coverage
- 22 new tests cover `_require_sdk()` and `PROVIDER_API_KEY_ENV`

## Files touched

- `src/helping_hands/lib/ai_providers/types.py` (add `_require_sdk`)
- `src/helping_hands/lib/ai_providers/anthropic.py` (use `_require_sdk`)
- `src/helping_hands/lib/ai_providers/openai.py` (use `_require_sdk`)
- `src/helping_hands/lib/ai_providers/google.py` (use `_require_sdk`)
- `src/helping_hands/lib/ai_providers/litellm.py` (use `_require_sdk`)
- `src/helping_hands/lib/ai_providers/ollama.py` (use `_require_sdk`)
- `src/helping_hands/lib/hands/v1/hand/model_provider.py` (add `PROVIDER_API_KEY_ENV`)
- `src/helping_hands/lib/hands/v1/hand/cli/goose.py` (import shared mapping)
- `src/helping_hands/lib/hands/v1/hand/cli/opencode.py` (import shared mapping)
- `tests/test_v265_provider_import_guard_api_key_map.py` (22 new tests)
- `tests/test_v159_all_exports.py` (update `__all__` count)
- `tests/test_anthropic_provider.py` (update error message match)
- `tests/test_openai_provider.py` (update error message match)
- `tests/test_google_provider.py` (update error message match)
- `tests/test_litellm_provider.py` (update error message match)
- `tests/test_ollama_provider.py` (update error message match)
- `tests/test_provider_build_inner.py` (update error message matches)
- `docs/PLANS.md` (index update)
