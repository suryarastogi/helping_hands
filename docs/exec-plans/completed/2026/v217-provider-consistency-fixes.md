# v217 — Provider Consistency Fixes

**Status:** Completed
**Completed:** 2026-03-16
**Created:** 2026-03-16
**Goal:** Fix provider inconsistencies: Google LangChain missing `streaming`
parameter, Google provider empty-contents validation gap, and Claude CLI silent
GPT model filtering.

## Context

The `build_langchain_chat_model()` function passes `streaming=streaming` to
OpenAI, Ollama, Anthropic, and LiteLLM providers but omits it for Google
(`ChatGoogleGenerativeAI`). This means Google's LangGraph backend ignores the
streaming preference.

The Google provider's `_complete_impl` filters out empty-content messages but
doesn't validate that the resulting `contents` list is non-empty, leading to
a cryptic downstream error instead of a clear validation message.

The Claude Code CLI hand silently filters out GPT models in
`_resolve_cli_model()` without logging, making it hard to diagnose why a
user's model choice was ignored.

## Tasks

- [x] Pass `streaming=streaming` to `ChatGoogleGenerativeAI` in `model_provider.py`
- [x] Add empty-contents validation in Google provider `_complete_impl`
- [x] Add `logger.warning` in Claude CLI `_resolve_cli_model` when GPT model filtered
- [x] Add tests for all three fixes
- [x] Run lint, type check, and tests — verify green
- [x] Update PLANS.md, Week-12 log, and move plan to completed

## Completion criteria

- Google LangChain model respects streaming parameter
- Google provider raises clear error on all-empty messages
- Claude CLI logs warning when GPT model is silently dropped
- All tests pass, no lint/format/type regressions
