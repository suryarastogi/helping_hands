# Design Philosophy

Core design patterns and principles for helping_hands.

## Guiding principles

1. **Plain data between layers** — Modules communicate through dicts and
   dataclasses. No tight coupling between config, repo, hands, and entry points.

2. **Streaming by default** — AI responses stream to the caller as they arrive.
   No buffering full responses unless explicitly needed.

3. **Explicit configuration** — No module-level singletons. `Config` is loaded
   once and threaded through function calls.

4. **Path safety** — All filesystem operations route through
   `meta/tools/filesystem.py` with `resolve_repo_target()` preventing
   path traversal outside the repo root.

5. **Minimal side effects** — Hands attempt commit/push/PR by default, but
   all side effects can be disabled (`--no-pr`). Execution and web tools
   are opt-in.

## Patterns

### Hand abstraction

The `Hand` base class defines the contract: `run()` for sync, `stream()` for
async iteration. Implementations are split into separate modules under
`hands/v1/hand/` to prevent monolithic growth.

### Provider resolution

Model strings like `gpt-5.2` or `anthropic/claude-sonnet-4-5` resolve through
the `ai_providers/` layer. Each provider wraps its SDK with a common interface
and lazy initialization.

### Two-phase CLI hands

CLI-backed hands (`codex`, `claude`, `goose`, `gemini`, `opencode`) run two
subprocess phases: (1) initialize/learn the repo, (2) execute the task.
This separation gives the external CLI tool repo context before acting.

### Finalization

Commit/push/PR logic is centralized in the `Hand` base class so all backends
share the same branch naming, token auth, and PR body generation.

## Anti-patterns to avoid

- **Global state** — No module-level caches or singletons
- **Cross-layer imports** — CLI/server should not import each other's internals
- **Monolithic files** — Keep hand implementations in separate modules
- **Implicit auth** — Always use explicit token-based push, never OS credential prompts
