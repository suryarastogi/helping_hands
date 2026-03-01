# AGENT.md — Conventions Summary

> The canonical agent guidance file lives at the **repo root**: [`AGENT.md`](../../AGENT.md).
> This note summarizes the key conventions for vault readers.

## Code Style

- **Python 3.12+**, `uv` for dependencies, `ruff` for lint/format (line length 88)
- Type hints everywhere (`X | None` not `Optional[X]`)
- Google-style docstrings on public functions/classes
- Absolute imports: `from helping_hands.lib.config import Config`
- `snake_case` functions/variables, `PascalCase` classes, `_` prefix for private helpers

## Design Principles

- **Plain data between layers** — dicts/dataclasses, not tight coupling
- **No global state** — config is passed explicitly
- **Streaming-first** — AI responses stream to the terminal as they arrive
- **Explicit side-effect toggle** — PR creation defaults on; disable with `--no-pr`
- **System tool isolation** — all file operations route through `lib/meta/tools/filesystem.py`

## Key Recurring Decisions

- Hand implementations stay split under `lib/hands/v1/hand/` — no monolithic `hand.py`
- Model resolution goes through `lib/ai_providers/` + `model_provider.py`
- Git pushes use token-authenticated non-interactive remotes
- Iterative hands preload `README.md`, `AGENT.md`, and bounded tree on iteration 1
- All request models validate input at the API boundary (min_length, bounds)
- Health check exceptions are logged at warning level for observability

## Testing

- pytest in `tests/`, coverage enabled by default
- `uv run pytest -v` runs the full suite
- E2E integration is opt-in (`HELPING_HANDS_RUN_E2E_INTEGRATION=1`)

## For More Detail

See the full repo-root [[AGENT.md]] for auto-update sections, dependency table, and tone/communication preferences.
