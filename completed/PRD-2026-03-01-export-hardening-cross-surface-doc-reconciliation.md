# PRD: Export Hardening and Cross-Surface Doc Reconciliation

**Created:** 2026-03-01
**Completed:** 2026-03-01
**Branch:** helping-hands/claudecodecli-4bd7467a

## Goal

Close remaining module `__all__` export gaps, and reconcile stale metrics across all documentation surfaces (obsidian, README, AGENT.md, MkDocs).

## Measurable Success Criteria

- All source modules with public API surfaces declare `__all__` — **achieved** (40 modules)
- All public classes have Google-style docstrings — **verified** (all already present)
- Test counts and API page counts are consistent across obsidian, AGENT.md, and Project todos.md — **achieved**
- Lint (`ruff check .`) and tests (`pytest -v`) pass clean — **achieved** (624 passed)

## TODO

- [x] **1. Add `__all__` to `atomic.py` and `iterative.py`** — 2 modules added, total now 40
- [x] **2. Verify class-level docstrings** — audit confirmed all 25+ public classes already have Google-style docstrings
- [x] **3. Fix obsidian `Project todos.md` stale test count** — 579 → 624
- [x] **4. Fix obsidian `Architecture.md` inline API page count** — "36 total" → "37 total"
- [x] **5. Reconcile `__all__` counts across AGENT.md, Architecture.md, Concepts.md** — 38 → 40
- [x] **6. Run lint + tests to verify all changes pass** — 624 passed, 0 lint errors

## Non-Goals

- Adding new tests (test coverage is adequate at 624 tests)
- Modifying MkDocs pages (already 100% coverage at 37 pages)
- Changing any runtime behavior

---

## Activity Log

- **2026-03-01:** Created PRD in `active/`. Audited codebase for `__all__`, docstring, and doc consistency gaps.
- **2026-03-01:** Added `__all__` to `atomic.py` (`["AtomicHand"]`) and `iterative.py` (`["BasicAtomicHand", "BasicLangGraphHand"]`). Fixed RUF022 sort order on `iterative.py`.
- **2026-03-01:** Verified all 25+ public classes already have Google-style docstrings — no additions needed.
- **2026-03-01:** Fixed obsidian `Project todos.md` test count (579→624) and `Architecture.md` inline API page count (36→37).
- **2026-03-01:** Updated `__all__` counts across AGENT.md (38→40), Architecture.md footer (38→40), Concepts.md footer (38→40).
- **2026-03-01:** Added project log entry to `2026-W10.md`.
- **2026-03-01:** Lint clean, 624 tests passing. PRD completed and moved to `completed/`.
