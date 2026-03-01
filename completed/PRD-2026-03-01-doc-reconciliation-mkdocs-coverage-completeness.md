# PRD: Documentation Reconciliation & MkDocs Coverage Completeness

**Status:** Completed 2026-03-01
**Created:** 2026-03-01
**Scope:** Cross-surface doc reconciliation, MkDocs coverage gaps, obsidian vault sync

## Problem Statement

After multiple rounds of documentation and test improvements, several cross-surface inconsistencies remain:

1. **Stale test count** — obsidian `Project todos.md` references 488 tests; actual count is 510.
2. **Missing MkDocs page** — `placeholders.py` module exists but has no MkDocs API doc page or nav entry.
3. **Incomplete docs/index.md links** — `ai_providers/types` API page exists in mkdocs.yml nav but is not linked from `docs/index.md`.
4. **Ambiguous hand module count** — Architecture.md and Project todos.md reference "13 Hand modules" without clarifying this means 12 implementation files + 1 package surface.
5. **API page count drift** — multiple surfaces reference "35 API pages" but adding placeholders.py will bring the count to 36.
6. **Obsidian AGENT.md summary** — the vault summary references the root AGENT.md but doesn't reflect latest conventions added in 2026-03-01 session.

## Success Criteria

- [x] `obsidian/docs/Project todos.md` test count updated to 510
- [x] `docs/api/lib/hands/v1/hand/placeholders.md` created with correct module reference
- [x] `mkdocs.yml` nav updated with placeholders entry
- [x] `docs/index.md` updated with links to `ai_providers/types` and `hand/placeholders`
- [x] `obsidian/docs/Architecture.md` hand module count clarified
- [x] API page count references updated across surfaces (35 → 36)
- [x] `obsidian/docs/Project todos.md` design notes updated with latest conventions
- [x] `obsidian/docs/AGENT.md` refreshed with latest recurring decisions summary
- [x] Lint and format pass clean

## TODO

- [x] 1. Fix stale test count in `obsidian/docs/Project todos.md` (488 → 510)
- [x] 2. Create `docs/api/lib/hands/v1/hand/placeholders.md` for the backward-compat shim module
- [x] 3. Add placeholders entry to `mkdocs.yml` nav under hands
- [x] 4. Add missing `ai_providers/types` and `hand/placeholders` links to `docs/index.md`
- [x] 5. Clarify hand module count in `obsidian/docs/Architecture.md` (12 impl + 1 package = 13 pages)
- [x] 6. Update API page count references (35 → 36) in obsidian docs
- [x] 7. Refresh `obsidian/docs/AGENT.md` summary with latest 2026-03-01 conventions
- [x] 8. Update `obsidian/docs/Project todos.md` design notes section with latest test/doc stats
- [x] 9. Run `uv run ruff check .` and `uv run ruff format --check .` to verify clean state

## Activity Log

- 2026-03-01: PRD created after auditing all 4 documentation surfaces (README, docs/, obsidian/, AGENT.md) and identifying 6 reconciliation gaps.
- 2026-03-01: Executed all 9 TODO items. Fixed stale counts, added placeholders.py MkDocs page, updated index cross-references, clarified hand module count, refreshed obsidian AGENT.md summary and Project todos design notes. Lint/format clean.
