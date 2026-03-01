# PRD: Documentation Reconciliation, Obsidian Sync & Code Quality

## Goal

Reconcile all documentation surfaces (README, AGENT.md, CLAUDE.md, Obsidian vault, MkDocs API docs, docstrings) so they are consistent, current, and cross-linked. Address the highest-impact code quality improvements identified by audit.

## Measurable Success Criteria

- All doc surfaces agree on feature counts (tests, API pages, backends, providers)
- Obsidian vault has current-week project log entry and accurate timestamps
- Obsidian docs reference correct module counts and feature state
- Cross-references between doc surfaces are valid and bidirectional
- No stale numbers or outdated feature descriptions remain across surfaces
- All tests pass after changes (`uv run pytest -v`)

## Non-Goals

- Refactoring `server/app.py` (2829 lines — separate effort, high risk)
- Adding dedicated test files for E2EHand/LangGraphHand/AtomicHand (separate effort)
- Splitting `celery_app.py` helpers into sub-modules

## TODO

- [x] **T1: Create W10 project log** — Add `obsidian/docs/Project Log/2026-W10.md` for current week (2–8 Mar 2026), update `Project Log.md` and `Weekly progress.md` index links
- [x] **T2: Obsidian Architecture.md timestamp & accuracy pass** — Verify module/file counts, add last-updated marker, fix any stale descriptions
- [x] **T3: Obsidian Concepts.md accuracy pass** — Verify feature descriptions match current codebase, add last-updated marker
- [x] **T4: Obsidian Home.md cross-reference audit** — Ensure all links to repo-root docs and external surfaces are valid
- [x] **T5: Obsidian AGENT.md summary sync** — Ensure convention summary matches latest root AGENT.md recurring decisions
- [x] **T6: docs/index.md cross-reference audit** — Verify all 36 API page links are present and valid
- [x] **T7: mkdocs.yml nav completeness** — Cross-check nav entries against filesystem API doc pages
- [x] **T8: README.md freshness check** — Verify feature descriptions, backend list, and examples are current
- [x] **T9: TODO.md freshness check** — Ensure all checklist items match current reality
- [x] **T10: Run tests** — `uv run pytest -v` to verify nothing is broken

---

## Activity Log

- **2026-03-01 T1:** Created `obsidian/docs/Project Log/2026-W10.md` for week of 2–8 Mar 2026. Updated `Project Log.md` "Latest" link and `Weekly progress.md` index with W10 entry.
- **2026-03-01 T2:** Verified Architecture.md module counts (12 impl + 1 package + 1 shim = 14, 36 API pages). Added last-updated timestamp footer. All descriptions match current codebase.
- **2026-03-01 T3:** Verified Concepts.md feature descriptions (hands, E2E, basic hands, CLI backends, providers, MCP, cron, skills, frontend, project log). Added last-updated timestamp footer. All current.
- **2026-03-01 T4:** Audited Home.md cross-references: wikilinks (Vision, Concepts, Architecture, Project todos, Project Log) and relative links (README.md, CLAUDE.md, AGENT.md, docs/index.md, completed/) all valid.
- **2026-03-01 T5:** Added 2 missing recurring decisions to Obsidian AGENT.md summary: exception handler ordering (catch subclass before parent) and skills payload validation. Now 14 key decisions listed, matching root AGENT.md.
- **2026-03-01 T6:** Found docs/index.md was missing 5 of 36 API page links (individual AI provider pages: openai, anthropic, google, litellm, ollama). Added all 5. Now 36/36 linked.
- **2026-03-01 T7:** Cross-checked mkdocs.yml nav (36 API entries + 1 index = 37 total) against 36 files on disk. All match — no orphans, no missing pages.
- **2026-03-01 T8:** README.md verified current: last-updated March 1 2026, all backends listed, CLI examples accurate, app mode docs match compose.yaml.
- **2026-03-01 T9:** TODO.md verified current: all 8 milestones marked complete, 2 CI items appropriately deferred with rationale.
- **2026-03-01 T10:** `uv run pytest -v` — 510 passed, 4 skipped, 7.88s. `uv run ruff check . && uv run ruff format --check .` — all clean.
