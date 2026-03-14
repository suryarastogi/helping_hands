# Database schema

> Auto-generated reference. No database is currently used in CLI mode.

## App mode (planned)

App mode uses Postgres for job metadata and state. Schema TBD — currently
the Celery result backend (Redis) stores task results.

### Planned tables

| Table | Purpose |
|---|---|
| `jobs` | Task metadata (repo, prompt, status, timestamps) |
| `repos` | Indexed repositories (path, file count, last indexed) |
| `sessions` | Conversation sessions linking multiple jobs |
| `agent_logs` | AGENT.md updates and hand decisions |

No migrations exist yet. Schema will be defined when app mode is fully wired.
