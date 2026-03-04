# AGENTS.md — Multi-agent coordination guide

> This file describes how AI agents interact with the helping_hands codebase,
> including coordination rules when multiple agents run concurrently.

See [AGENT.md](AGENT.md) for single-agent conventions and coding style.

---

## Agent types

| Agent role | Entry point | Description |
|---|---|---|
| **CLI hand** | `uv run helping-hands` | Direct execution via iterative or CLI backend |
| **Worker hand** | Celery `build_feature` task | Async execution via FastAPI `/build` endpoint |
| **MCP agent** | `uv run helping-hands-mcp` | Tool-serving agent for IDE/editor integrations |

## Coordination rules

1. **Branch isolation** — Each hand run creates its own branch
   (`helping-hands/{backend}-{uuid}`). Agents must never push to another
   agent's branch.
2. **PR ownership** — Only one agent should own a PR at a time. Use
   `--pr-number` to resume an existing PR; do not create duplicates.
3. **Workspace layout** — Async runs use `{hand_uuid}/git/{repo}` workspace
   paths. Do not share workspace directories between concurrent agents.
4. **Config immutability** — Agents receive config at startup and must not
   modify shared environment variables or `.env` files during execution.
5. **AGENT.md updates** — Only one agent should update `AGENT.md` per session.
   In concurrent runs, defer updates to the primary/first agent.

## File ownership conventions

| Path pattern | Owner | Notes |
|---|---|---|
| `AGENT.md` | Primary agent | Updated at session end |
| `README.md` | Primary agent | Structural changes only |
| `src/helping_hands/**` | Any agent (via branch) | Must pass CI |
| `tests/**` | Any agent (via branch) | Must pass CI |
| `docs/**` | Any agent | Non-code, lower conflict risk |

## Communication between agents

Agents do not communicate directly. Coordination happens through:

- **Git branches** — Each agent works on its own branch
- **PR comments** — Status markers (`<!-- helping_hands:* -->`) for idempotent updates
- **Task status API** — `/tasks/{id}` for async status polling
- **Celery inspect** — Worker discovery via `/tasks/current`

---

*Last updated: 2026-03-04*
