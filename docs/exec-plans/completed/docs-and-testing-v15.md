# Execution Plan: Docs and Testing v15

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add unit tests for `build_langchain_chat_model()` and `build_atomic_client()` in model_provider.py; create provider abstraction design doc; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: model_provider.py builder function tests

- [x] `build_langchain_chat_model` -- OpenAI provider returns ChatOpenAI with correct args
- [x] `build_langchain_chat_model` -- Ollama provider returns ChatOpenAI with base_url/api_key from env
- [x] `build_langchain_chat_model` -- Anthropic provider returns ChatAnthropic, ImportError path
- [x] `build_langchain_chat_model` -- Google provider returns ChatGoogleGenerativeAI, ImportError path
- [x] `build_langchain_chat_model` -- LiteLLM provider returns ChatLiteLLM, ImportError path
- [x] `build_langchain_chat_model` -- unsupported provider raises RuntimeError
- [x] `build_atomic_client` -- OpenAI provider calls instructor.from_openai
- [x] `build_atomic_client` -- LiteLLM provider calls instructor.from_litellm
- [x] `build_atomic_client` -- LiteLLM provider raises when instructor lacks from_litellm
- [x] `build_atomic_client` -- unsupported provider raises RuntimeError

### Phase 2: Provider abstraction design doc

- [x] Create `docs/design-docs/provider-abstraction.md` covering model resolution, provider interface, adding new providers
- [x] Update `docs/design-docs/index.md`

### Phase 3: Validation

- [x] All tests pass (36 in test_hand_model_provider.py, all green)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Update `docs/PLANS.md`
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
