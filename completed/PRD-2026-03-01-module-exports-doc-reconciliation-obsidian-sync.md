# PRD: Module Exports, Documentation Reconciliation & Obsidian Sync

## Problem Statement

The codebase has 19 meaningful modules without `__all__` declarations, creating an implicit/ambiguous public API surface. Additionally, the Obsidian vault has stale test counts (579 vs actual 624) and is missing one PRD from the Completed PRDs index. These gaps reduce developer confidence in import boundaries and create cross-surface documentation drift.

## Success Criteria

1. All 18 meaningful source modules declare `__all__` with correct public symbols
2. Obsidian AGENT.md test count updated from 579 to 624
3. Completed PRDs index includes the missing PRD and correct count (25)
4. Cross-surface metrics (test count, API page count, module counts) are consistent
5. All existing tests still pass (624 tests)
6. `ruff check` and `ruff format --check` pass clean

## Non-Goals

- Adding new tests (test coverage is already comprehensive at 624 tests)
- Changing exception handling patterns (already hardened)
- Adding docstrings (already complete)
- Modifying functional behavior of any module

## TODO

- [x] **T1: AI provider `__all__` exports** — Add `__all__` to 5 provider modules (`openai.py`, `anthropic.py`, `google.py`, `litellm.py`, `ollama.py`)
- [x] **T2: CLI hand `__all__` exports** — Add `__all__` to 4 CLI hand modules (`claude.py`, `codex.py`, `goose.py`, `gemini.py`) + empty `__all__` for `cli/base.py`
- [x] **T3: Meta tools `__all__` exports** — Add `__all__` to `command.py`, `web.py`, `filesystem.py`
- [x] **T4: Remaining module `__all__` exports** — Add `__all__` to `langgraph.py`, `default_prompts.py`, `cli/main.py`, `server/app.py`, `server/celery_app.py`, `server/mcp_server.py`
- [x] **T5: Obsidian Completed PRDs index** — Add missing `obsidian-completeness-prd-workflow-doc-reconciliation` PRD, update count from 24 to 25
- [x] **T6: Obsidian AGENT.md test count** — Update 579 → 624 tests
- [x] **T7: Cross-surface reconciliation** — Verify all surfaces agree on test count (624), API pages (37), module count, `__all__` count; update AGENT.md recurring decisions
- [x] **T8: Lint and test verification** — Run `ruff check`, `ruff format --check`, and `pytest` to confirm no regressions

## Activity Log

- **2026-03-01 — Hand:** Created PRD with 8 TODO items after comprehensive audit of codebase.
- **2026-03-01 — Hand:** T1 complete — Added `__all__` to 5 AI provider modules (openai, anthropic, google, litellm, ollama).
- **2026-03-01 — Hand:** T2 complete — Added `__all__` to 5 CLI hand modules (claude, codex, goose, gemini, base).
- **2026-03-01 — Hand:** T3 complete — Added `__all__` to 3 meta tools modules (command, web, filesystem).
- **2026-03-01 — Hand:** T4 complete — Added `__all__` to 6 remaining modules (langgraph, default_prompts, cli/main, server/app, server/celery_app, server/mcp_server).
- **2026-03-01 — Hand:** T5 complete — Added missing PRD to Completed PRDs index, count updated 24→25.
- **2026-03-01 — Hand:** T6 complete — Updated Obsidian AGENT.md test count 579→624.
- **2026-03-01 — Hand:** T7 complete — Cross-surface reconciliation: updated root AGENT.md with `__all__` count (30 modules), updated Architecture.md and Concepts.md `__all__` counts, added W10 project log entry. All surfaces agree: 624 tests, 37 API pages, 30 `__all__` modules.
- **2026-03-01 — Hand:** T8 complete — `ruff check`, `ruff format --check`, and `pytest` all pass (624 tests, 0 failures). PRD moved to completed/.
