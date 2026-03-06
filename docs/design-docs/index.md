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

## Adding a design doc

1. Create a new `.md` file in this directory
2. Add it to this index with a one-line description
3. Include: context, decision, alternatives considered, consequences
