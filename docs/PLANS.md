# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [Docs and Testing v77](exec-plans/completed/docs-and-testing-v77.md) --
  E2E hand workflow design doc; extended docs structure validation tests (design doc source references, API docs completeness, PLANS.md structure, active plan consistency, key source files; 10 new); 1676 tests pass (completed 2026-03-06)

- [Docs and Testing v76](exec-plans/completed/docs-and-testing-v76.md) --
  Model-resolution design doc; extended docs structure validation tests (PLANS.md link resolution, design-docs count sync, tech-debt-tracker structure, TODO.md structure, completed plan content; 10 new); 1666 tests pass (completed 2026-03-06)


- [Docs and Testing v75](exec-plans/completed/docs-and-testing-v75.md) --
  Filesystem-security design doc; extended docs structure validation tests (FRONTEND.md sections, PRODUCT_SENSE.md sections, SECURITY.md sandboxing subsections, design doc content checks, ARCHITECTURE.md section count; 18 new); 1656 tests pass (completed 2026-03-06)

- [Docs and Testing v74](exec-plans/completed/docs-and-testing-v74.md) --
  Default-prompts design doc; extended docs structure validation tests (DESIGN.md sections, SECURITY.md sections, RELIABILITY.md sections, README.md sections, QUALITY_SCORE.md structure; 19 new); 1638 tests pass (completed 2026-03-06)

- [Docs and Testing v73](exec-plans/completed/docs-and-testing-v73.md) --
  PR description design doc; extended docs structure validation tests (ARCHITECTURE.md key paths, AGENTS.md sections, docs/index.md link resolution, CLAUDE.md sections; 17 new); 1619 tests pass (completed 2026-03-06)

- [Docs and Testing v72](exec-plans/completed/docs-and-testing-v72.md) --
  GitHub client design doc; extended docs structure validation tests (API docs link validity, completed plan structure, design-docs index count; 7 new); 1602 tests pass (completed 2026-03-06)

- [Docs and Testing v71](exec-plans/completed/docs-and-testing-v71.md) --
  Skills system design doc; extended docs structure validation tests (product-specs index, root-level docs, reference files, tech-debt-tracker module refs; 6 new); 1595 tests pass (completed 2026-03-06)

- [Docs and Testing v70](exec-plans/completed/docs-and-testing-v70.md) --
  CI pipeline design doc; docs structure validation tests (4 new); 1587 tests pass (completed 2026-03-06)

- [Docs and Testing v69](exec-plans/completed/docs-and-testing-v69.md) --
  Consolidate v63-v68 into 2026-03-06.md; deployment-modes design doc; mock_github_client fixture self-tests (11 new); Hand instantiation smoke tests (27 new); 1583 tests pass (completed 2026-03-06)

- [2026-03-06 consolidated](exec-plans/completed/2026-03-06.md) --
  v32-v68: PR description, schedule, E2E, server health, GitHub client, package re-exports, Docker sandbox, CLI subprocess, celery usage, iterative agents, atomic/LangGraph stream, frontend coverage to 82.3%, dead code docs, testing methodology, shared conftest fixtures, config refactor, repo-indexing/scheduling-system/error-handling/MCP-architecture/config-loading design docs; 1263 -> 1545 tests (completed 2026-03-06)
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
