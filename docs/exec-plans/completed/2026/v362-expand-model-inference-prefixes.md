# v362 — Expand Model Inference Prefixes

**Status:** Completed
**Created:** 2026-04-04

## Problem

`_infer_provider_name` in `model_provider.py` only recognizes three model
prefixes: `claude*` → Anthropic, `gemini*` → Google, `llama*` → Ollama.
All other bare model names fall through to OpenAI. This means common
open-source models that users typically run via Ollama (mistral, phi,
deepseek, qwen, mixtral, codellama, etc.) get incorrectly routed to OpenAI,
causing silent auth failures when no OpenAI API key is set.

Similarly, OpenAI reasoning models (`o1-*`, `o3-*`, `o4-mini`) don't start
with "gpt" — they happen to work today only because OpenAI is the default
fallback, but the intent isn't explicit and the function isn't self-documenting.

## Tasks

- [x] Expand `_infer_provider_name` with Ollama prefixes (mistral, mixtral,
  phi, codellama, deepseek, qwen, starcoder, vicuna, yi)
- [x] Add explicit OpenAI prefixes (gpt, o1, o3, o4)
- [x] Add `_OLLAMA_MODEL_PREFIXES` / `_OPENAI_MODEL_PREFIXES` constants
- [x] Add tests for each new prefix (14 inference + 4 constant + 3 resolve)
- [x] Update `docs/design-docs/model-resolution.md`
- [x] Update PLANS.md, INTENT.md, Week-14 consolidation

## Completion criteria

- `_infer_provider_name("mistral-7b")` returns `"ollama"`
- `_infer_provider_name("deepseek-coder-v2")` returns `"ollama"`
- `_infer_provider_name("o1-preview")` returns `"openai"`
- All existing tests pass unchanged
- Design doc updated
- 21 new tests added (14 inference + 4 constant + 3 resolve)
