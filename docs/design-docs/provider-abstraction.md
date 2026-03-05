# Provider Abstraction

**Status:** Accepted
**Date:** 2026-03-05

## Context

Helping hands supports multiple AI providers (OpenAI, Anthropic, Google, LiteLLM, Ollama). Each provider has a different SDK, different authentication, and different API shapes. Hands need a uniform way to resolve a user-supplied model string into a working provider client and to bridge that client into backend-specific runtime objects (LangChain chat models, Atomic Agents instructor clients).

## Decision

### Two-layer design

1. **Provider layer** (`lib/ai_providers/`) -- thin SDK wrappers with a common `AIProvider` interface.
2. **Model resolution layer** (`lib/hands/v1/hand/model_provider.py`) -- resolves user model strings and bridges providers into backend-specific objects.

### Provider interface (`AIProvider`)

All providers extend `AIProvider` (defined in `lib/ai_providers/types.py`):

```
AIProvider (abstract)
  name: str                    # "openai", "anthropic", etc.
  api_key_env_var: str         # "OPENAI_API_KEY", etc.
  default_model: str           # "gpt-5.2", "llama3.2:latest", etc.
  install_hint: str            # "uv add openai"
  inner -> Any                 # Lazy-loaded SDK client
  _build_inner() -> Any        # Construct the SDK client
  _complete_impl(...) -> Any   # Provider-specific completion call
  complete(prompt) -> Any      # Public API (normalizes messages, calls _complete_impl)
  acomplete(prompt) -> Any     # Async wrapper via asyncio.to_thread
```

Key properties:
- **Lazy inner client**: `inner` is not built until first access via `_build_inner()`.
- **Graceful import errors**: `_build_inner()` catches `ImportError` and raises `RuntimeError` with install hints.
- **Message normalization**: `complete()` accepts both bare strings and chat-style message lists.

### Model resolution (`resolve_hand_model`)

User model input flows through a resolution chain:

```
User input          Resolution path
-----------         ---------------
"default" / None    -> Ollama provider, provider default model
"ollama"            -> Provider name match, provider default model
"anthropic/claude"  -> "provider/model" split
"claude-sonnet-4-5" -> _infer_provider_name() heuristic -> "anthropic"
"gpt-5.2"          -> Falls through to "openai" (default)
```

The result is a `HandModel(provider, model, raw)` dataclass.

### Backend adapters

Two adapter functions bridge `HandModel` into backend-specific objects:

**`build_langchain_chat_model(hand_model, streaming)`** -- Used by `BasicLangGraphHand`:
- OpenAI/Ollama -> `langchain_openai.ChatOpenAI`
- Anthropic -> `langchain_anthropic.ChatAnthropic`
- Google -> `langchain_google_genai.ChatGoogleGenerativeAI`
- LiteLLM -> `langchain_community.chat_models.ChatLiteLLM`

**`build_atomic_client(hand_model)`** -- Used by `BasicAtomicHand`:
- OpenAI -> `instructor.from_openai(provider.inner)`
- LiteLLM -> `instructor.from_litellm(provider.inner.completion)`

Both raise `RuntimeError` for unsupported providers with actionable messages.

### Provider registry

`PROVIDERS` dict in `lib/ai_providers/__init__.py` maps provider names to singleton instances. All resolution goes through this registry.

## Adding a new provider

1. Create `lib/ai_providers/<name>.py` with a class extending `AIProvider`
2. Implement `_build_inner()` and `_complete_impl()`
3. Export a singleton (`<NAME>_PROVIDER = <Name>Provider()`)
4. Register in `lib/ai_providers/__init__.py` PROVIDERS dict
5. Add prefix heuristic to `_infer_provider_name()` if the provider has recognizable model names
6. Add LangChain/Atomic adapter branches in `model_provider.py` if needed
7. Add tests for `_build_inner()`, `_complete_impl()`, and any new adapter branches

## Alternatives considered

- **Factory pattern with provider registration**: More dynamic but adds complexity for 5 providers.
- **Single adapter class per backend**: Would duplicate resolution logic across backends.
- **Config-driven provider mapping**: Less flexible for providers with different SDK shapes.

## Consequences

- Adding a provider requires touching 3-4 files but each change is small and well-isolated.
- Backend-specific adapter functions keep LangChain/Atomic dependencies out of the provider layer.
- Lazy `inner` loading means import errors surface at runtime, not import time -- intentional to allow optional dependencies.
