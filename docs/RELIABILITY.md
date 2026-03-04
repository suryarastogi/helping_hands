# Reliability

## Error Handling Strategy

- Hands catch and report AI provider errors gracefully — a failed completion doesn't crash the session
- Task result normalization (`task_result.py`) ensures server endpoints always return JSON, even for exceptions
- Celery tasks use Redis broker with configurable retry policies

## Testing

- pytest with branch coverage enabled by default
- CI runs on Python 3.12, 3.13, and 3.14
- Integration tests are marked separately (`@pytest.mark.integration`) and require external services
- Frontend has separate Vitest coverage

## Monitoring

- Flower provides Celery task monitoring in server mode
- FastAPI endpoints expose task status for polling/WebSocket clients

## Graceful Degradation

- Optional extras (langchain, atomic, server) fail at import time with clear messages, not at runtime
- CLI hands wrap external processes and report exit codes/stderr on failure
- Missing `GITHUB_TOKEN` skips PR creation rather than crashing
