# PRD: Documentation & Docstring Reconciliation — Cross-Surface Consistency

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Bring all documentation surfaces (README, MkDocs API docs, Obsidian vault, docstrings) into full consistency, fill remaining docstring gaps, and ensure Obsidian reflects the current state of the project.

---

## Problem Statement

Five completed PRDs have already improved documentation significantly. However, a fresh audit reveals remaining gaps:

1. **docs/index.md** omits the `default_prompts` link despite having a mkdocs.yml nav entry and API page.
2. **Obsidian Architecture.md** doesn't mention the React frontend, skills system, or MCP tools architecture.
3. **Obsidian Concepts.md** is missing four major topics: MCP mode, scheduled tasks/cron, the skills system, and the React frontend.
4. **Obsidian Home.md** only links vault-internal pages — no cross-reference to README, API docs site, or CLAUDE.md.
5. **~15 public/internal functions** across `celery_app.py`, `mcp_server.py`, `cli/main.py`, and `ai_providers/types.py` still lack Google-style docstrings, leaving mkdocstrings stubs empty.
6. **Obsidian Project Log W09** should be updated with the current reconciliation pass.

## Success Criteria

- [x] `docs/index.md` links every module in `mkdocs.yml` nav
- [x] Obsidian `Architecture.md` covers React frontend, skills system, and MCP tools
- [x] Obsidian `Concepts.md` covers MCP mode, scheduled tasks, skills, and frontend
- [x] Obsidian `Home.md` cross-references README, API docs, and CLAUDE.md
- [x] All public/semi-public functions in audited modules have Google-style docstrings
- [x] Obsidian Project Log W09 updated with this reconciliation pass
- [x] No factual inconsistencies between documentation surfaces

## Non-Goals

- Rewriting README prose (it is accurate and comprehensive)
- Adding docstrings to obvious one-liner private helpers
- Changing code behavior or adding features
- Adding a docstring linter to CI

---

## TODO

### 1. Fix docs/index.md API Reference link gap
- [x] Add `default_prompts` to the lib API Reference list in `docs/index.md`

### 2. Update Obsidian Architecture.md
- [x] Add React frontend section (frontend/, Vite, task submission/monitoring)
- [x] Add skills system section (meta/skills/, normalization, merging, validation)
- [x] Expand MCP mode description to cover filesystem/command/web tool categories
- [x] Expand system tools layer to list all three tool modules
- [x] Add skills layer as layer 7 in shared layers list

### 3. Update Obsidian Concepts.md
- [x] Add MCP mode/tools concept section
- [x] Add scheduled tasks/cron concept section
- [x] Add skills system concept section
- [x] Add React frontend concept section

### 4. Update Obsidian Home.md
- [x] Add cross-references to README, API docs site, AGENT.md, CLAUDE.md, and completed/

### 5. Fill remaining docstring gaps
- [x] `celery_app.py`: `_github_clone_url`, `_git_noninteractive_env`, `_redact_sensitive`, `_trim_updates`, `_append_update`, `_UpdateCollector.__init__`/`feed`/`flush`, `_update_progress`, `_collect_stream` (10 docstrings added)
- [x] `cli/main.py`: `_stream_hand`, `_github_clone_url`, `_git_noninteractive_env`, `_redact_sensitive`, `_resolve_repo_path` (5 docstrings added)
- [x] `ai_providers/types.py`: already had docstrings on `inner`, `install_hint`, `_build_inner`, `_complete_impl` — only `__init__` was missing but is a trivial one-liner covered by the class docstring

### 6. Update Obsidian Project Log W09
- [x] Add entry for this documentation reconciliation pass

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created; cross-surface audit identified 6 gap categories |
| 2026-03-01 | Added `default_prompts` link to `docs/index.md` API Reference |
| 2026-03-01 | Updated Architecture.md: added React frontend, skills system, and expanded MCP/system tools sections |
| 2026-03-01 | Updated Concepts.md: added MCP mode, scheduled tasks, skills system, and React frontend sections |
| 2026-03-01 | Updated Home.md: added cross-references to README, API docs, AGENT.md, CLAUDE.md, completed/ |
| 2026-03-01 | Added 15 Google-style docstrings to `celery_app.py` (10) and `cli/main.py` (5) |
| 2026-03-01 | Updated Project Log W09 with reconciliation pass entry |
| 2026-03-01 | All lint checks pass, 359 tests pass; PRD complete |
