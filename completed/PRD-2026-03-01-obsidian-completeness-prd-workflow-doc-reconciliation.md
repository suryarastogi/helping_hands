# PRD: Cross-Surface Documentation Reconciliation, Obsidian Completeness & PRD Workflow

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Fix remaining documentation surface gaps — missing `validation.py` references, absent completed-PRD index in Obsidian, missing `active/` directory for PRD workflow, and README not linking to design docs. Reconcile all five documentation surfaces (README, CLAUDE.md, Obsidian vault, MkDocs API docs, AGENT.md).

## Problem Statement

After 23 completed PRDs, several small cross-surface gaps remain:

1. **`validation.py` missing from README project structure tree** — the recently-extracted shared validation module (`lib/validation.py`) is in MkDocs and `docs/index.md` but absent from the README file tree and Obsidian Architecture.md layers list.
2. **No completed-PRD index in Obsidian** — 23 completed PRDs exist in `completed/` but the Obsidian vault has no index page for navigating them.
3. **`active/` directory missing from repo** — PRD workflow expects `active/` → `completed/` movement but `active/` didn't exist and won't persist without a `.gitkeep`.
4. **README lacks design docs reference** — users have no way to discover the Obsidian vault or design notes from the README.
5. **Obsidian Architecture.md missing validation layer** — shared validation utilities are a new cross-cutting concern not reflected in the architecture layers.

## Success Criteria

- [x] `active/` directory created with `.gitkeep` for git persistence
- [x] README project structure tree includes `validation.py`
- [x] Obsidian Architecture.md includes validation as a shared utility layer
- [x] Obsidian vault has a "Completed PRDs" index page linked from Home.md
- [x] README includes a "Design documentation" section pointing to `obsidian/docs/`
- [x] Cross-surface consistency verified: all five surfaces agree on module counts, test counts, and feature descriptions
- [x] Project log entry added for this PRD

## Non-Goals

- Rewriting existing prose or docstrings that are already accurate
- Adding new MkDocs API pages (validation.md already exists as page 37)
- Changing code behavior or tests
- Restructuring the completed/ directory naming convention

## TODO

- [x] 1. Create `active/` directory with `.gitkeep`
- [x] 2. Add `validation.py` to README project structure tree (under `lib/`)
- [x] 3. Add validation utilities layer to Obsidian Architecture.md (between Config and Repo index layers)
- [x] 4. Create Obsidian `Completed PRDs.md` index page listing all 23 completed PRDs with dates and themes
- [x] 5. Update Obsidian Home.md to link to the new Completed PRDs page
- [x] 6. Add "Design & documentation" section to README pointing to `obsidian/docs/`, `docs/`, and `completed/`
- [x] 7. Update Obsidian `Project todos.md` to mention the new `active/` directory for PRD workflow
- [x] 8. Add project log entry to `2026-W10.md` documenting this reconciliation
- [x] 9. Final cross-surface audit: verify all surfaces agree on module counts and features

## Activity Log

- **2026-03-01 — PRD created.** Audited all five documentation surfaces. Identified 5 concrete gaps. Created `active/` directory. PRD ready for execution.
- **2026-03-01 — All TODO items executed.** Added `validation.py` to README project structure tree. Added validation utilities layer to Obsidian Architecture.md. Created `Completed PRDs.md` index page with all 23 PRDs catalogued by date and theme. Updated Obsidian Home.md with PRDs section linking to completed PRDs index. Added "Design documentation" section to README linking to obsidian vault, API docs, completed PRDs, AGENT.md, CLAUDE.md. Updated Project todos.md with PRD workflow description. Added project log entry to 2026-W10.md. Final cross-surface audit confirmed: 37 MkDocs API pages on disk match mkdocs.yml nav, all 5 documentation surfaces consistent. PRD complete.
