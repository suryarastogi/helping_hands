# Reliability

How helping_hands maintains reliability across modes and backends.

## Error handling strategy

- **Config errors**: Fail fast with clear messages (missing tokens, bad paths).
- **Repo errors**: `FileNotFoundError` for missing paths, validated at entry.
- **Backend errors**: Each hand catches its own errors and returns them in
  `HandResponse.metadata` with error details.
- **Subprocess errors**: CLI hands (Claude, Codex, Gemini) handle process
  failures, timeouts, and non-zero exit codes.

## Timeouts

- CLI hand subprocess: 300s default (configurable).
- Celery tasks: Configured via Celery settings.
- MCP tools: No timeout (controlled by client).

## Resilience patterns

- **No global state**: Config passed explicitly; no module-level singletons
  that can get stale.
- **Immutable config**: `Config` is a frozen dataclass. No accidental mutation.
- **Graceful degradation**: Optional dependencies (dotenv, langchain, atomic)
  handled with try/except imports.
