# PRD: Cross-Surface Doc Reconciliation & Packaging Polish

**Date:** 2026-03-01
**Status:** Complete
**Scope:** Fix documentation inconsistencies across Obsidian vault, add missing pyproject.toml metadata, update project log

## Goals

- Reconcile API page counts across all documentation surfaces (Obsidian AGENT.md, Project todos.md say 36; actual count is 37)
- Add `[project.urls]` metadata to pyproject.toml for standard Python packaging
- Ensure Obsidian vault has consistent "last updated" footers
- Update project log with current session activity

## Non-Goals

- No code changes (all source modules are fully documented and tested)
- No new API doc pages (37 pages cover all modules)
- No docstring additions (all public APIs have Google-style docstrings)

## TODO

- [x] 1. Fix Obsidian AGENT.md API page count: "36" → "37" (line 43)
- [x] 2. Fix Obsidian Project todos.md API page count: "36" → "37" (line 11)
- [x] 3. Add `[project.urls]` section to pyproject.toml (Homepage, Repository, Documentation, Issues)
- [x] 4. Add "Last updated" footer to Obsidian Home.md for consistency with other vault docs
- [x] 5. Add project log entry for this session in 2026-W10.md
- [x] 6. Verify cross-surface consistency: README, CLAUDE.md, AGENT.md (root), Obsidian vault, MkDocs, docs/index.md all agree on module counts, test counts, feature descriptions

## Acceptance Criteria

- [x] All documentation surfaces agree on: 37 API pages, 579 tests, 14 hand modules
- [x] pyproject.toml includes valid `[project.urls]` with 4 standard links
- [x] Obsidian Home.md has a "Last updated" footer
- [x] Project log 2026-W10 has an entry for this reconciliation session

---

## Activity Log

- **2026-03-01 — Audit:** Explored all 4 documentation surfaces + source code. Found 2 API page count mismatches (obsidian/docs/AGENT.md:43, obsidian/docs/Project todos.md:11), missing pyproject.toml URLs, and missing Home.md footer. 37 API doc pages on disk confirmed. All docstrings complete. 579 tests referenced consistently in Architecture.md and Project Log.
- **2026-03-01 — Execute:** Fixed API page count in obsidian/docs/AGENT.md (36 → 37) and obsidian/docs/Project todos.md (36 → 37). Added `[project.urls]` section to pyproject.toml with 4 standard links. Added "Last updated: 2026-03-01" footer to obsidian/docs/Home.md. Added project log entry in 2026-W10.md.
- **2026-03-01 — Verify:** Grepped all surfaces for "36 API", "37 API", "579 tests", "14 hand modules". All active documentation surfaces now consistent. Remaining "36" references are in historical project log entries and completed PRDs (correct — they record point-in-time state).
- **2026-03-01 — Complete:** All 6 TODO items done. PRD moved to completed/.
