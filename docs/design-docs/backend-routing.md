# Backend Routing

How helping_hands resolves backend names to Hand subclass instances across CLI,
server, and Celery entry points.

## Context

Users specify a backend via `--backend` (CLI) or a form/API field (server).
Each entry point must validate the string, resolve it to the correct `Hand`
subclass, and handle optional-dependency failures gracefully.  The routing
logic is intentionally duplicated across entry points (CLI, server, Celery)
rather than centralized, because each path has different import constraints
and error reporting needs.

## Decision

### CLI routing (`cli/main.py`)

The CLI parser accepts backend names via `argparse` `choices`:

```
basic-langgraph, basic-atomic, basic-agent, codexcli,
claudecodecli, docker-sandbox-claude, goose, geminicli, opencodecli
```

Routing uses an `if/elif` chain that maps each name to a Hand constructor.
`basic-agent` falls through to `BasicAtomicHand` (the `else` branch).

Optional-dependency errors (`ModuleNotFoundError`) are caught and produce
user-facing messages with install instructions (`uv sync --extra langchain`
or `uv sync --extra atomic`).

### Server routing (`server/app.py`)

The FastAPI server defines `BackendName` as a `Literal` type and validates
incoming strings through `_parse_backend()`, which normalizes
(strip + lowercase) and looks up in `_BACKEND_LOOKUP`.  Invalid backends
raise `ValueError` with available choices.

The Pydantic `BuildRequest` model uses `BackendName` as a field type, giving
automatic validation on the API path.  The HTML form path uses `_parse_backend`
directly.

### Celery routing (`server/celery_app.py`)

The Celery task uses `_normalize_backend()` which validates against
`_SUPPORTED_BACKENDS` (a set) and maps `basic-agent` to `basic-atomic`
at runtime.  This two-value return (`requested`, `runtime`) preserves the
original backend name for logging while using the canonical implementation.

### Backend-to-Hand mapping

| Backend name | Hand class | Module | Optional extra |
|---|---|---|---|
| `e2e` | `E2EHand` | `hand/e2e.py` | -- |
| `basic-langgraph` | `BasicLangGraphHand` | `hand/langgraph.py` | `langchain` |
| `basic-atomic` | `BasicAtomicHand` | `hand/atomic.py` | `atomic` |
| `basic-agent` | `BasicAtomicHand` | `hand/atomic.py` | `atomic` |
| `codexcli` | `CodexCLIHand` | `hand/cli/codex.py` | -- |
| `claudecodecli` | `ClaudeCodeHand` | `hand/cli/claude.py` | -- |
| `docker-sandbox-claude` | `DockerSandboxClaudeCodeHand` | `hand/cli/docker_sandbox_claude.py` | -- |
| `goose` | `GooseCLIHand` | `hand/cli/goose.py` | -- |
| `geminicli` | `GeminiCLIHand` | `hand/cli/gemini.py` | -- |
| `opencodecli` | `OpenCodeCLIHand` | `hand/cli/opencode.py` | -- |

### Key invariants

- `basic-agent` is an alias for `basic-atomic` (same Hand class)
- CLI hands require no optional extras (they shell out to external CLIs)
- Iterative hands (`basic-langgraph`, `basic-atomic`) require their
  respective `--extra` packages
- All backends share the same finalization path (base `Hand._finalize_repo_pr`)
- `docker-sandbox-claude` is only available via CLI (not in `_BACKEND_LOOKUP`
  or `_SUPPORTED_BACKENDS`)

## Alternatives considered

- **Centralized registry**: A single `BACKEND_REGISTRY` dict mapping names to
  classes.  Rejected because import-time resolution of optional-dependency
  classes would fail in minimal installations.
- **Plugin system**: Auto-discover Hand subclasses via entry points.  Rejected
  as over-engineering for a fixed set of backends.

## Consequences

- Adding a new backend requires updating three locations: CLI `choices` +
  `if/elif`, server `BackendName` + `_BACKEND_LOOKUP`, and Celery
  `_SUPPORTED_BACKENDS`.
- The duplication is intentional: each entry point can tailor error messages
  and import handling to its context.
- `docker-sandbox-claude` is CLI-only by design (requires Docker Desktop
  plugin not available in server containers).
