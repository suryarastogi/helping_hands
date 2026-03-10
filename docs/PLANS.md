# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [2026-03-10](exec-plans/completed/2026-03-10.md) --
  v104-v109: Dead code cleanup, server routing completion, E2E draft PR, Celery helper extraction, stream collector tests, health check tests, tech-debt cleanup, server helper unit tests, ty type checker in CI; 3031 -> 3409 tests
- [2026-03-07 Week 10](exec-plans/completed/2026/Week-10.md) --
  v0-v103: Docs infrastructure, 28 design docs, massive validation test suite, provider tests, Config edge cases, Playwright e2e tests, exec-plan workflow; 0 -> 3031 tests
- [2026-03-02 Week 9](exec-plans/completed/2026/Week-9.md) --
  Multi-backend expansion (Goose, Gemini, Ollama), React frontend launch, animated office world view, cron scheduling, usage tracking, skills/tools refactor; 0 tests (pre-test-suite)
- [2026-02-23 Week 8](exec-plans/completed/2026/Week-8.md) --
  Project inception: Hand abstraction, AI providers, Celery, MCP server, GitHub integration, Claude Code CLI, E2E flow; 0 tests (pre-test-suite)

## How plans work

1. Plans are created in `docs/exec-plans/active/` with a descriptive filename
2. Each plan has a status, creation date, tasks, and completion criteria
3. When all tasks are done, the plan moves to `docs/exec-plans/completed/`
4. The tech debt tracker (`docs/exec-plans/tech-debt-tracker.md`) captures
   ongoing technical debt items that don't warrant a full plan
