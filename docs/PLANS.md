# Plans

Index of execution plans for helping_hands development.

## Active plans

- [v102 - Docs and testing improvements](exec-plans/active/v102-docs-testing-improvements.md) --
  Ollama provider test enhancements (singleton identity, class attrs, delegation), Hand instantiation/HandResponse test enhancements, plan consolidation

## Completed plans

- [2026-03-07 consolidated](exec-plans/completed/2026-03-07.md) --
  v80-v101: Docker sandbox design doc, command execution design doc, local stack design doc, usage-monitoring design doc, backend routing design doc, docs organization and testing improvements, plan consolidation, design-docs index categorization, cross-reference validation tests, AGENTS.md consistency tests, design doc quality tests, source-to-test mapping validation, QUALITY_SCORE accuracy tests, doc timestamp freshness tests, tech-debt priority validation, RELIABILITY/FRONTEND/docs-index structure tests, PRODUCT_SENSE/QUALITY_SCORE/AGENTS cross-validation, completed plan chronology, references directory, active plan structure tests, SECURITY.md iterative security validation, DESIGN.md anti-patterns/pattern subsection/error recovery tests, testing-methodology coverage table tests, CLAUDE.md architecture tests, docs/index.md CLI examples tests, ARCHITECTURE.md key paths/usage monitoring/task result/hand table/design principles/layers validation, DESIGN.md meta tools/finalization tests, SECURITY.md recommendations/API key handling tests, RELIABILITY.md Docker sandbox/async fallback/finalization tests, AGENTS.md communication/file ownership tests, DESIGN.md two-phase CLI hooks/health checks/GitHub client/lifecycle/testing patterns validation tests, FRONTEND.md API endpoints/component structure tests, SECURITY.md subprocess execution tests, AGENT.md structural/cross-reference validation, API docs directory validation, product-specs content validation, local-stack doc/script validation, scheduling-system/skills-system doc content validation, DESIGN.md skill catalog section tests, RELIABILITY.md heartbeat/task status tests, FRONTEND.md sync requirements tests, docs/index.md runtime flow/design-docs completeness tests, design doc source reference tests, tech-debt/QUALITY_SCORE consistency tests, PLANS.md structural validation tests, design doc content validation (config-loading/default-prompts/error-handling/model-resolution/deployment-modes/pr-description/backend-routing/hand-abstraction/filesystem-security/github-client/ci-pipeline/mcp-architecture/repo-indexing/two-phase-cli-hands/task-lifecycle/e2e-hand-workflow), conftest fixture validation tests, ARCHITECTURE.md backend listing tests, SECURITY.md recommendation coverage tests, web-tools/core-beliefs/testing-methodology design doc content validation tests, TODO.md/ARCHITECTURE.md external integrations/DESIGN.md PR description+scheduled tasks/SECURITY.md Gemini+container/RELIABILITY.md iterative+idempotency/docs-index API+CLI/product-specs+generated directory/design doc cross-refs/exec-plans chronology/tech-debt structure/conftest docs/QUALITY_SCORE module coverage/PRODUCT_SENSE completeness validation tests, dedicated litellm/anthropic provider tests, provider test file/design-doc category/test naming/cross-ref/opencode docs validation tests, enhanced Google provider tests, Config edge case and from_env precedence tests; 1740 -> 2987 tests (completed 2026-03-07)

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
