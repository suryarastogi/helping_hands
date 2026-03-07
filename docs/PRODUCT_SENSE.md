# Product Sense

Product direction and user-facing priorities for helping_hands.

## What helping_hands is

An AI-powered repo builder that takes a codebase as input and uses AI to add
features, fix bugs, and evolve code. It runs as CLI, web server, or MCP tool
server.

## Target users

1. **Solo developers** — Use CLI mode to get AI help on personal projects
2. **Teams** — Use app mode to queue and schedule AI-assisted code changes
3. **Tool builders** — Use MCP mode to integrate helping_hands into editors/IDEs

## Key value propositions

- **Multi-backend flexibility** — Choose from LangGraph, Atomic Agents, Codex,
  Claude, Goose, Gemini, or OpenCode backends
- **Convention-aware** — Learns repo patterns via AGENT.md and applies them
- **Full lifecycle** — From understanding code to creating PRs
- **Self-improving** — Agent guidance improves across sessions

## Product priorities (current)

1. **Reliability** — Runs should complete successfully and produce useful changes
2. **Backend coverage** — Support the most popular AI coding tools
3. **Ease of setup** — Minimize configuration required to get started
4. **Observability** — Clear status, logs, and monitoring for all run modes

## Implemented capabilities

- **Scheduled runs** -- Celery Beat + RedBeat for recurring tasks with cron
  validation, enable/disable, and one-shot trigger support
- **MCP tool server** -- `helping-hands-mcp` exposes filesystem tools
  (`read_file`, `write_file`, `mkdir`, `path_exists`), execution tools, and
  repo indexing over stdio or streamable-http transport
- **Skill catalog** -- Built-in skills staged to a temp directory during CLI
  hand runs; extensible via `--skills` selection

## Future directions

- Multi-repo orchestration
- Custom skill authoring for domain-specific tasks
- Quality scoring of AI-generated changes before PR creation
