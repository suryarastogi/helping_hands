# PRD: Documentation Reconciliation, Type Safety & Error Handling Hardening

## Problem Statement

The codebase has three documentation surfaces (README/CLAUDE.md, MkDocs API docs, Obsidian vault) that have drifted apart. Key inconsistencies include stale model names in Obsidian, missing MCP/skills/cron documentation in CLAUDE.md, an incomplete project structure tree in README.md, and undocumented backend aliases. Additionally, the type checker reports 4 errors in `schedules.py`, and the PR finalization catch-all silently swallows exceptions without logging.

## Success Criteria

- [x] All 4 `ty` type errors in `schedules.py` resolved
- [x] `_finalize_repo_pr` catch-all logs exception with traceback
- [x] CLAUDE.md architecture section includes MCP mode, skills, cron scheduling, basic-agent alias
- [x] Anthropic model names consistent across all docs (`claude-sonnet-4-5` not `claude-3-5-sonnet-latest`)
- [x] Obsidian Architecture.md lists `model_provider.py` and `pr_description.py`, documents PR description generation step
- [x] Obsidian Concepts.md uses current model names and documents execution/web toggles
- [x] TODO.md updated with implemented features (MCP, skills, frontend, PR description, verbose logging)
- [x] README.md install section mentions `--extra github` and `--extra mcp`

## Non-Goals

- Adding new tests for server modules (0% coverage modules need dedicated PRD)
- Adding `model_provider.py` test coverage (separate effort)
- Redesigning the documentation architecture
- CI pipeline changes

## TODO

- [x] Fix 4 `ty` type errors in `schedules.py` via type narrowing assertions
- [x] Add `logger.exception()` to `_finalize_repo_pr` catch-all in `base.py`
- [x] Reconcile CLAUDE.md: add MCP mode, skills, cron, `basic-agent` alias, `--extra docs`
- [x] Fix Anthropic model name inconsistencies: `README.md`, `obsidian/docs/Concepts.md`
- [x] Update Obsidian `Architecture.md`: add `model_provider.py`, `pr_description.py`, PR description generation step
- [x] Update Obsidian `Concepts.md`: current model names, execution/web toggles
- [x] Update `TODO.md` with implemented features (MCP, skills, frontend, PR description, verbose logging, config validation)
- [x] Update `README.md` install instructions to mention `--extra github` and `--extra mcp`

## Activity Log

- 2026-03-01T05:00 — PRD created, work begins
- 2026-03-01T05:01 — Fixed 4 `ty` type errors in `schedules.py` via `assert` narrowing after guard calls
- 2026-03-01T05:01 — Added `logger.warning()`/`logger.exception()` to all `_finalize_repo_pr` catch blocks in `base.py`
- 2026-03-01T05:02 — Reconciled CLAUDE.md: added MCP mode, skills, cron, `basic-agent` alias, `model_provider.py`, `pr_description.py`
- 2026-03-01T05:02 — Fixed stale `claude-3-5-sonnet-latest` → `claude-sonnet-4-5` in README.md and Concepts.md
- 2026-03-01T05:03 — Updated Architecture.md: added `model_provider.py`/`pr_description.py` to file list, PR description step to finalization workflow, `basic-agent` alias note
- 2026-03-01T05:03 — Added execution/web toggle docs to Concepts.md basic hand semantics
- 2026-03-01T05:04 — Updated TODO.md with MCP, skills, frontend, PR description, verbose logging, config validation, API validation, exception hardening
- 2026-03-01T05:04 — Updated README.md install section with `--extra github` and `--extra mcp`
- 2026-03-01T05:05 — All checks pass: ruff lint ✓, ruff format ✓, ty ✓, 488 tests ✓. PRD complete.
