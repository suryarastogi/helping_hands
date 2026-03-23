# Design Docs

Index of design documents for helping_hands.

## Core

- [Core Beliefs](core-beliefs.md) — Fundamental design principles
- [Config Loading](config-loading.md) — Env loading precedence, dotenv, normalization, and frozen config
- [Error Handling](error-handling.md) — Recovery patterns, fallback chains, and narrow failure boundaries
- [Default Prompts](default-prompts.md) — Smoke test prompt structure, directive flow, and CLI/server sharing

## Hands

- [Hand Abstraction](hand-abstraction.md) — Hand class hierarchy and extension model
- [Two-Phase CLI Hands](two-phase-cli-hands.md) — Subprocess architecture, retry logic, and sandboxing
- [E2E Hand Workflow](e2e-hand-workflow.md) — Clone/branch/edit/commit/push/PR lifecycle, resume flow, dry-run
- [Docker Sandbox](docker-sandbox.md) — MicroVM isolation via Docker Desktop sandboxes, lifecycle, env forwarding
- [PR Description](pr-description.md) — Generation flow, prompt engineering, parsing, fallback chain, and env config
- [Backend Routing](backend-routing.md) — Backend name resolution to Hand subclasses across CLI, server, and Celery

## Providers and Models

- [Provider Abstraction](provider-abstraction.md) — AI provider interface, model resolution, and backend adapters
- [Model Resolution](model-resolution.md) — HandModel dataclass, provider inference heuristics, LangChain/Atomic adapters

## Tools and Skills

- [Filesystem Security](filesystem-security.md) — Path confinement via resolve_repo_target, MCP sharing, and sandboxing boundaries
- [Command Execution](command-execution.md) — Path-confined Python/Bash runners, tool registry, CLI guidance translation
- [Web Tools](web-tools.md) — DuckDuckGo search, URL browsing, HTML extraction, content truncation
- [Skills System](skills-system.md) — Catalog discovery, normalization, staging, and prompt injection
- [Repo Indexing](repo-indexing.md) — Repository ingestion, tree walking, and RepoIndex design

## Infrastructure

- [Deployment Modes](deployment-modes.md) — CLI vs Server vs MCP runtime modes
- [MCP Architecture](mcp-architecture.md) — Tool registration, transport selection, and repo isolation
- [Task Lifecycle](task-lifecycle.md) — Celery task enqueue, progress streaming, update buffering, result normalization
- [Scheduling System](scheduling-system.md) — RedBeat, ScheduleManager CRUD, cron presets, trigger-now
- [GitHub Client](github-client.md) — Authentication, clone/branch/PR lifecycle, and token safety
- [CI Pipeline](ci-pipeline.md) — GitHub Actions workflows, matrix strategy, coverage, and docs deployment
- [Local Stack](local-stack.md) — Native process management for local development with Docker data services
- [Usage Monitoring](usage-monitoring.md) — Claude Code OAuth usage polling, Keychain token retrieval, Postgres persistence

## Frontend

- [Multiplayer Hand World](multiplayer-hand-world.md) — WebSocket-based real-time avatar synchronization in Hand World

## Quality

- [Testing Methodology](testing-methodology.md) — Coverage-guided iteration, test patterns, and dead code documentation

## Adding a design doc

1. Create a new `.md` file in this directory
2. Add it to this index with a one-line description
3. Include: context, decision, alternatives considered, consequences
