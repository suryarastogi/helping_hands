# Design Docs

Index of design documents for helping_hands.

## Documents

- [Core Beliefs](core-beliefs.md) — Fundamental design principles
- [Hand Abstraction](hand-abstraction.md) — Hand class hierarchy and extension model
- [Two-Phase CLI Hands](two-phase-cli-hands.md) — Subprocess architecture, retry logic, and sandboxing
- [Provider Abstraction](provider-abstraction.md) — AI provider interface, model resolution, and backend adapters
- [Testing Methodology](testing-methodology.md) — Coverage-guided iteration, test patterns, and dead code documentation
- [Error Handling](error-handling.md) — Recovery patterns, fallback chains, and narrow failure boundaries
- [MCP Architecture](mcp-architecture.md) — Tool registration, transport selection, and repo isolation
- [Config Loading](config-loading.md) — Env loading precedence, dotenv, normalization, and frozen config
- [Repo Indexing](repo-indexing.md) — Repository ingestion, tree walking, and RepoIndex design
- [Scheduling System](scheduling-system.md) — RedBeat, ScheduleManager CRUD, cron presets, trigger-now
- [Deployment Modes](deployment-modes.md) — CLI vs Server vs MCP runtime modes
- [CI Pipeline](ci-pipeline.md) — GitHub Actions workflows, matrix strategy, coverage, and docs deployment
- [Skills System](skills-system.md) — Catalog discovery, normalization, staging, and prompt injection
- [GitHub Client](github-client.md) — Authentication, clone/branch/PR lifecycle, and token safety
- [PR Description](pr-description.md) — Generation flow, prompt engineering, parsing, fallback chain, and env config
- [Default Prompts](default-prompts.md) — Smoke test prompt structure, directive flow, and CLI/server sharing
- [Filesystem Security](filesystem-security.md) — Path confinement via resolve_repo_target, MCP sharing, and sandboxing boundaries
- [Model Resolution](model-resolution.md) — HandModel dataclass, provider inference heuristics, LangChain/Atomic adapters
- [E2E Hand Workflow](e2e-hand-workflow.md) — Clone/branch/edit/commit/push/PR lifecycle, resume flow, dry-run
- [Task Lifecycle](task-lifecycle.md) — Celery task enqueue, progress streaming, update buffering, result normalization
- [Web Tools](web-tools.md) — DuckDuckGo search, URL browsing, HTML extraction, content truncation
- [Docker Sandbox](docker-sandbox.md) — MicroVM isolation via Docker Desktop sandboxes, lifecycle, env forwarding

## Adding a design doc

1. Create a new `.md` file in this directory
2. Add it to this index with a one-line description
3. Include: context, decision, alternatives considered, consequences
