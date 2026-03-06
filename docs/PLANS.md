# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [Docs and Testing v68](exec-plans/completed/docs-and-testing-v68.md) --
  Add scheduling-system design doc; make_fake_module conftest fixture; conftest self-tests (5 new); 1545 tests pass (completed 2026-03-06)

- [Docs and Testing v67](exec-plans/completed/docs-and-testing-v67.md) --
  Add repo-indexing design doc; shared mock_github_client conftest fixture; top-level package import/docstring tests (21 new); 1540 tests pass (completed 2026-03-06)

- [Docs and Testing v66](exec-plans/completed/docs-and-testing-v66.md) --
  Refactor test_config.py to monkeypatch; add Config frozen/dotenv/verbose tests (5 new); add config-loading design doc; 1519 tests pass (completed 2026-03-06)


- [Docs and Testing v65](exec-plans/completed/docs-and-testing-v65.md) --
  Web dataclass construction and _decode_bytes edge case tests (19 tests); MCP architecture design doc; updated testing methodology stats; 1514 tests pass (completed 2026-03-06)

- [Docs and Testing v64](exec-plans/completed/docs-and-testing-v64.md) --
  Refactor test_cli_hand_goose.py to shared `make_cli_hand` fixture; add conftest fixture self-tests (10 tests); update AGENTS.md with Docker Sandbox and scheduled agents; add error-handling design doc; 1495 tests pass (completed 2026-03-06)

- [Docs and Testing v63](exec-plans/completed/docs-and-testing-v63.md) --
  Consolidate v32-v62 into `2026-03-06.md` (31 files -> 1); add `make_cli_hand` factory fixture to conftest.py; refactor 5 CLI hand test files to use shared fixture; 1485 tests pass (completed 2026-03-06)

- [2026-03-06 consolidated](exec-plans/completed/2026-03-06.md) --
  v32-v62: PR description, schedule, E2E, server health, GitHub client, package re-exports, Docker sandbox, CLI subprocess, celery usage, iterative agents, atomic/LangGraph stream, frontend coverage to 82.3%, dead code docs, testing methodology, shared conftest fixtures; 1263 -> 1485 tests (completed 2026-03-06)
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
