# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [2026-03-07 consolidated](exec-plans/completed/2026-03-07.md) --
  v80-v88: Docker sandbox design doc, command execution design doc, docs organization and testing improvements, plan consolidation, design-docs index categorization, cross-reference validation tests, AGENTS.md consistency tests, design doc quality tests, source-to-test mapping validation, QUALITY_SCORE accuracy tests, doc timestamp freshness tests, tech-debt priority validation, RELIABILITY/FRONTEND/docs-index structure tests, PRODUCT_SENSE/QUALITY_SCORE/AGENTS cross-validation, completed plan chronology, references directory, active plan structure tests, SECURITY.md iterative security validation, DESIGN.md anti-patterns/pattern subsection tests, testing-methodology coverage table tests, CLAUDE.md architecture tests, docs/index.md CLI examples tests, ARCHITECTURE.md key paths/usage monitoring/task result validation, DESIGN.md error recovery/meta tools/finalization tests, SECURITY.md recommendations/API key handling tests, RELIABILITY.md Docker sandbox/async fallback tests, AGENTS.md communication/file ownership tests, DESIGN.md two-phase CLI hooks/health checks/GitHub client/lifecycle/testing patterns validation tests, FRONTEND.md API endpoints/component structure tests, SECURITY.md subprocess execution tests; 1740 -> 2076 tests (completed 2026-03-07)

- [2026-03-06 consolidated](exec-plans/completed/2026-03-06.md) --
  v32-v79: PR description, schedule, E2E, server health, GitHub client, package re-exports, Docker sandbox, CLI subprocess, celery usage, iterative agents, atomic/LangGraph stream, frontend coverage to 82.3%, dead code docs, testing methodology, shared conftest fixtures, config refactor, Hand smoke tests, docs structure validation, 21 design docs (repo-indexing through web-tools); 1263 -> 1717 tests (completed 2026-03-06)
- [2026-03-05 consolidated](exec-plans/completed/2026-03-05.md) --
  v5-v31: Pure helper, CLI hand, AI provider, iterative hand, Docker sandbox, celery, schedule, MCP server, web tool, PR description, and package-level test suites; provider abstraction design doc; ARCHITECTURE.md, DESIGN.md, SECURITY.md, RELIABILITY.md updates; 470 -> 1256 tests (completed 2026-03-05)
- [2026-03-04 consolidated](exec-plans/completed/2026-03-04.md) --
  v1-v4: Established docs structure, product specs, hand abstraction design doc, iterative hand tests, AI provider tests, two-phase CLI hands design doc, SECURITY.md sandboxing; 50 -> 470 tests (completed 2026-03-04)

## How plans work

1. Plans are created in `docs/exec-plans/active/` with a descriptive filename
2. Each plan has a status, creation date, tasks, and completion criteria
3. When all tasks are done, the plan moves to `docs/exec-plans/completed/`
4. The tech debt tracker (`docs/exec-plans/tech-debt-tracker.md`) captures
   ongoing technical debt items that don't warrant a full plan
