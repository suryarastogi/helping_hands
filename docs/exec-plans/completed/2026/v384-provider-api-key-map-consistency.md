# v384 — Provider API Key Map Consistency

**Created:** 2026-04-05
**Status:** Completed
**Scope:** `model_provider.py`, tests

## Problem

`PROVIDER_API_KEY_ENV` in `model_provider.py` is missing the `litellm` provider
entry. All five providers are registered in `PROVIDERS` (`__init__.py`), but
only four appear in `PROVIDER_API_KEY_ENV`. This means CLI hands (goose,
opencode) that check auth status via `PROVIDER_API_KEY_ENV.get(provider)` return
`None` for litellm models, silently skipping the auth status report.

Additionally, there is no structural test ensuring `PROVIDER_API_KEY_ENV` stays
in sync with the `PROVIDERS` registry — the existing test hardcodes "all four
providers" rather than deriving from the source of truth.

## Tasks

- [x] Add `_PROVIDER_LITELLM: "LITELLM_API_KEY"` to `PROVIDER_API_KEY_ENV`
- [x] Update docstring to clarify Ollama maps to host, not API key
- [x] Update existing test `test_has_all_four_providers` → `test_has_all_providers`
  (dynamic check against `PROVIDERS` registry)
- [x] Add `test_maps_litellm_to_correct_env` test
- [x] Add structural consistency test: every key in `PROVIDERS` must appear in
  `PROVIDER_API_KEY_ENV`
- [x] Run tests, verify clean

## Completion criteria

- `PROVIDER_API_KEY_ENV` contains entries for all providers in `PROVIDERS`
- Structural tests prevent future drift between the two dicts
- All existing tests pass
- `uv run ruff check .` clean

## Files changed

- `src/helping_hands/lib/hands/v1/hand/model_provider.py`
- `tests/test_v265_provider_import_guard_api_key_map.py`
