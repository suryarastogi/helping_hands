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
- GitHub API calls wrapped with `GithubException` handling — clear messages with actionable hints
- E2E idempotency: branch collision handling, draft PR mode, PR reuse guard
- No-op exception patterns (`except Exception: raise`) are noise — only catch when handling/logging
- Hand constructors use concrete `Config`/`RepoIndex` types (via `TYPE_CHECKING`) instead of `Any`
- `Config.__post_init__` validates repo format, model name patterns, and skill names at creation time
- CLI `--verbose` wires to `logging.basicConfig()`; silent exception blocks use `logger.debug()`
- Exception handler ordering: catch subclass exceptions before parent classes (e.g. `UnicodeError` before `ValueError`)
- Skills payload validation: reject empty/missing payloads at the validation layer, not downstream
- Exception specificity: catch `(ValueError, TypeError, OSError)` instead of bare `except Exception` in CLI hands
- Recursive retry depth: `_invoke_cli_with_cmd` retries bounded by `_MAX_CLI_RETRY_DEPTH` (default 2)

## Documentation

- MkDocs: **37 API doc pages** covering all 14 hand modules (12 impl + 1 package + 1 backward-compat shim) plus all subsystems (including `validation`)
- CLI hand base docstrings: `_TwoPhaseCLIHand` public/semi-public methods documented for mkdocstrings completeness
- PEP 561: `py.typed` marker + `Typing :: Typed` classifier in `pyproject.toml`

## Testing

- pytest in `tests/`, coverage enabled by default — **579 tests passing** (as of 2026-03-01)
- `uv run pytest -v` runs the full suite
- E2E integration is opt-in (`HELPING_HANDS_RUN_E2E_INTEGRATION=1`)
- Key coverage areas: filesystem (40), CLI hands (111 incl. stream/interrupt), schedule manager (22), Celery helpers (15), skills (34), MCP (17), server app (47), AI providers (28)
- All four CLI hand implementations have dedicated unit tests (model filtering, auth detection, fallback/retry, defaults injection)
- `stream()`, `interrupt()`, `_terminate_active_process()` have dedicated tests
- Server/MCP internal helpers have dedicated tests (task extraction, Flower/Celery integration, health checks, config endpoints)

## For More Detail

See the full repo-root [[AGENT.md]] for auto-update sections, dependency table, and tone/communication preferences.
