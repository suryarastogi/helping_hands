# Design Principles

## Core Beliefs

1. **Explicit over implicit** — Configuration is passed, never global. No singletons, no module-level state.
2. **Streaming-first** — AI responses stream to the terminal as they arrive. Blocking aggregation is a last resort.
3. **Composition over inheritance** — Hands share behavior through the base class but extend via composition (tools, providers, skills).
4. **Plain data boundaries** — Modules communicate through dicts and dataclasses, not by importing each other's internals.
5. **Path safety by default** — All file operations route through `resolve_repo_target()` to prevent traversal.

## Design Patterns

- **Strategy pattern** for Hands — same interface, swappable backends
- **Adapter pattern** for AI providers — uniform `complete()`/`acomplete()` over vendor SDKs
- **Registry pattern** for tools and skills — declarative registration, runtime dispatch

## Anti-Patterns (Avoided)

- Monolithic hand module — kept split under `hands/v1/hand/`
- Hard-coded provider clients in hands — routed through `ai_providers/`
- Unconfined file access — always through `filesystem.py`
