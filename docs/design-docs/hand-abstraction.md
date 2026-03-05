# Design Doc: Hand Abstraction

**Status:** Accepted
**Created:** 2026-03-04

## Context

helping_hands supports multiple AI backends (OpenAI, Anthropic, LangGraph,
Atomic Agents, and external CLIs like Claude Code, Codex, Goose, Gemini,
OpenCode). Each backend has different invocation patterns, streaming models,
and configuration needs. We need a single interface that:

- Lets callers (CLI, server, MCP) run any backend interchangeably.
- Centralizes git/GitHub finalization (commit, push, PR) so it isn't
  duplicated across backends.
- Allows new backends to be added with minimal boilerplate.

## Decision

All backends implement the `Hand` abstract base class
(`lib/hands/v1/hand/base.py`), which defines:

```
Hand
├── run(prompt) -> HandResponse       # blocking
├── stream(prompt) -> AsyncIterator   # streaming
├── interrupt() / reset_interrupt()   # cooperative cancellation
└── _finalize_repo_pr(...)            # shared git/PR workflow
```

### Extension hierarchy

```
Hand (ABC)
├── E2EHand                    # clone → provider.complete → commit → PR
├── IterativeHand              # multi-turn loop with @@READ/@@FILE parsing
│   ├── BasicLangGraphHand     # LangGraph agent loop
│   └── BasicAtomicHand        # Atomic Agents loop
└── _TwoPhaseCLIHand           # subprocess init + task phases
    ├── ClaudeCodeHand
    ├── CodexCLIHand
    ├── GooseCLIHand
    ├── GeminiCLIHand
    └── OpenCodeCLIHand
```

### Key design choices

1. **Finalization in base class.** Every hand calls `_finalize_repo_pr()` after
   its AI work completes. This keeps commit/push/PR logic in one place and
   avoids drift between backends.

2. **Two-phase CLI pattern.** CLI hands run the external tool twice: once for
   repository learning (phase 1), once for task execution (phase 2). This
   gives the external CLI context about the repo before attempting edits.

3. **Config + RepoIndex injection.** Hands receive a `Config` and `RepoIndex`
   at construction. No hand reads environment variables for its core
   behavior (CLI hands read env vars only for command resolution and
   container wrapping, which are backend-specific concerns).

4. **Tool and skill resolution at init.** The base `Hand.__init__` resolves
   enabled tool categories and skill catalog entries once, making them
   available to any subclass that needs to inject tool/skill guidance
   into prompts.

## Alternatives considered

- **Strategy pattern with a runner.** A `HandRunner` class that accepts a
  strategy object. Rejected because the current inheritance approach is
  simpler and each hand has enough shared state (config, repo_index,
  interrupt event) that composition would add indirection without benefit.

- **Plugin/registry system.** Auto-discover hands via entry points. Deferred
  as premature — the current `__init__.py` mapping is explicit and easy to
  follow. Can be added later if third-party hands become a real use case.

## Consequences

- Adding a new CLI backend requires subclassing `_TwoPhaseCLIHand` and
  setting ~5 class attributes. See `cli/opencode.py` as the minimal example.
- Non-CLI backends (LangGraph, Atomic) subclass `IterativeHand` and
  implement the provider-specific agent loop.
- The `base.py` module is large (~620 lines) because finalization logic
  is substantial. This is acceptable because the logic is cohesive —
  splitting it would scatter a single workflow across multiple files.
