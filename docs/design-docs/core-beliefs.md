# Core Beliefs

Foundational design beliefs that guide architectural decisions in helping_hands.

## 1. AI agents should work with repos, not against them

Agents read and respect existing conventions (via AGENT.md, README.md, repo
structure). They don't impose their own style — they learn the project's style
and follow it.

## 2. Multiple backends are better than one

Different AI tools have different strengths. The Hand abstraction lets users
choose the best backend for their task without changing their workflow.

## 3. Side effects must be explicit and reversible

- PR creation is on by default but can be disabled (`--no-pr`)
- Execution tools are off by default (`--enable-execution`)
- Each run creates its own branch (reversible via branch delete)
- E2E updates are idempotent (same PR updated, not duplicated)

## 4. Agents should be observable

- Streaming output shows work in progress
- Heartbeats indicate liveness during quiet periods
- Task status APIs enable external monitoring
- PR comments and descriptions document what was done

## 5. Configuration over convention

- No magic defaults that require understanding internals
- Environment variables documented in README with clear purpose
- CLI flags override env vars override built-in defaults
- Model strings are explicit (`provider/model` format supported)
