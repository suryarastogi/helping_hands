# Frontend

helping_hands does not currently have a web frontend. The primary interfaces are:

## Current interfaces

1. **CLI** (`helping-hands <repo>`): Terminal-based interactive mode.
2. **HTTP API** (`/build`, `/tasks/{id}`, `/health`): FastAPI endpoints for
   app mode.
3. **MCP server** (`helping-hands-mcp`): Model Context Protocol for AI client
   integration (Claude Desktop, Cursor).
4. **Flower** (app mode): Celery monitoring UI at the default Flower port.

## Future considerations

A web UI for app mode would provide:
- Job submission and status tracking
- Repo browser with indexed file tree
- Conversation history and diff viewer
- Backend selection and configuration

No frontend work is currently planned. The CLI and API cover current use cases.
