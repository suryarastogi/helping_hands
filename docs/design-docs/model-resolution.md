# Model Resolution

How helping_hands resolves user-provided model strings into provider wrappers
and backend-specific runtime objects.

## Context

Users specify models in many forms: bare names (`gpt-5.2`), provider-prefixed
(`anthropic/claude-sonnet-4-5`), provider-only (`ollama`), or nothing at all
(`default`).  The model resolution layer normalizes all of these into a
`HandModel` triple — (provider, model, raw input) — that downstream backends
consume without caring about the parsing details.

The resolution logic lives in `lib/hands/v1/hand/model_provider.py` and builds
on the provider registry from `lib/ai_providers/`.

## HandModel dataclass

```python
@dataclass(frozen=True)
class HandModel:
    provider: AIProvider   # resolved provider wrapper (lazy-init SDK client)
    model: str             # concrete model name for the provider
    raw: str               # original user input, preserved for logging
```

`HandModel` is frozen to prevent accidental mutation after resolution.  The
`raw` field carries the unmodified user input so error messages and logs can
reference exactly what the user typed.

## Resolution flow

`resolve_hand_model(model)` processes input through four priority stages:

1. **Default** — empty, `None`, or `"default"` maps to the Ollama provider with
   its default model.  This lets local development work out of the box without
   an API key.

2. **Provider name** — if the input exactly matches a provider key in `PROVIDERS`
   (e.g. `"ollama"`, `"openai"`), the provider's default model is used.

3. **Slash-separated** — `"provider/model"` is split on the first `/`.  If the
   left side matches a known provider, the right side becomes the model name
   (with fallback to the provider's default model if the right side is empty).
   If the left side is not a known provider, resolution falls through to
   inference.

4. **Prefix inference** — bare model names are matched against common prefixes:
   `claude*` to Anthropic, `gemini*` to Google, `llama*` to Ollama, everything
   else to OpenAI.

This ordering means explicit forms always win over heuristics.  The fallthrough
from stage 3 (unrecognized `provider/model`) to stage 4 handles cases like
`openrouter/gpt-5.2` where the prefix is not a registered provider — the full
string is treated as a model name and the provider is inferred from it.

## Backend adapters

Once a `HandModel` is resolved, backend-specific adapters construct runtime
objects:

### LangChain adapter (`build_langchain_chat_model`)

Used by `BasicLangGraphHand`.  Maps providers to LangChain chat model classes:

| Provider | LangChain class | Notes |
|---|---|---|
| `openai` | `ChatOpenAI` | Standard OpenAI SDK |
| `ollama` | `ChatOpenAI` | OpenAI-compatible via `OLLAMA_BASE_URL` (default `localhost:11434/v1`) |
| `anthropic` | `ChatAnthropic` | Requires `langchain-anthropic` extra |
| `google` | `ChatGoogleGenerativeAI` | Requires `langchain-google-genai` extra |
| `litellm` | `ChatLiteLLM` | Requires `langchain-community` + `litellm` extras |

Optional LangChain packages are imported lazily inside the function body and
raise `RuntimeError` with install instructions when missing.  This keeps the
core library free of heavy LangChain dependencies.

### Atomic adapter (`build_atomic_client`)

Used by `BasicAtomicHand`.  Uses `instructor` to wrap provider SDK clients:

| Provider | Method | Notes |
|---|---|---|
| `openai` | `instructor.from_openai()` | Wraps the OpenAI client from `AIProvider.inner` |
| `litellm` | `instructor.from_litellm()` | Requires `instructor` with litellm support |

Other providers are not supported by the Atomic backend — users must use an
OpenAI-compatible model.

## Design decisions

- **Ollama as default** — local-first philosophy.  Users can run the tool
  without any API keys for experimentation.
- **Frozen dataclass** — prevents accidental mutation after resolution.
  Backends receive an immutable model selection.
- **Lazy SDK imports** — LangChain and Atomic dependencies are imported only
  when the corresponding backend is selected, keeping the base install lean.
- **Heuristic inference as last resort** — prefix matching (`claude*` to
  Anthropic) is convenient but imprecise.  The slash-separated form
  (`anthropic/model-name`) is always preferred for unambiguous resolution.
- **Provider registry as source of truth** — `PROVIDERS` dict from
  `lib/ai_providers/__init__.py` is the single registry.  Model resolution
  never creates provider instances independently.

## Consequences

- Adding a new provider requires: (1) an entry in `PROVIDERS`, (2) optionally
  a prefix heuristic in `_infer_provider_name`, (3) a case in the LangChain
  and/or Atomic adapter if the backend needs it.
- Unrecognized slash-prefixed models fall through to inference rather than
  erroring, which may surprise users if they misspell a provider name.  The
  `raw` field in `HandModel` helps debug these cases.
- The Atomic backend has a narrower provider surface than LangChain, which is
  documented in the unsupported-provider error messages.
