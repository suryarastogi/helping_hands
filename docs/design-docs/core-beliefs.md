# Core Beliefs

These beliefs guide every design decision in helping_hands. They are non-negotiable — if a change violates one of these, it needs a strong justification and a design doc.

## 1. Explicit over implicit

Configuration is passed, never global. No singletons, no module-level state. Every function receives what it needs through arguments. This makes testing straightforward and eliminates hidden coupling between modules.

**Practical test:** Can you call this function in a test without touching any global state? If not, refactor.

## 2. Streaming-first

AI responses stream to the terminal as they arrive. Blocking aggregation is a last resort. Users should see progress immediately — waiting for a full response before showing anything is unacceptable for long-running AI tasks.

**Practical test:** Does this hand implementation support `stream()` alongside `run()`? If not, add it.

## 3. Composition over inheritance

Hands share behavior through the base class but extend via composition (tools, providers, skills). Deep inheritance hierarchies make it hard to reason about behavior. Prefer injecting capabilities through constructor arguments.

**Practical test:** Does adding a new capability require modifying the base class? If so, consider composition instead.

## 4. Plain data boundaries

Modules communicate through dicts and dataclasses, not by importing each other's internals. This keeps module boundaries clean and prevents tight coupling.

**Practical test:** Does this import cross a module boundary (e.g., `server/` importing from `cli/`)? If so, extract the shared type into `lib/`.

## 5. Path safety by default

All file operations route through `resolve_repo_target()` to prevent directory traversal. There are no exceptions — every path touching the filesystem must be validated.

**Practical test:** Does this file operation use `resolve_repo_target()`? If not, it's a security bug.
