# PRD: Package Exports, Error Enrichment & Doc Reconciliation

## Goal

Close the remaining structural gaps in the helping_hands codebase: missing `__all__` exports in package `__init__.py` files, vague error messages in core filesystem module, unsafe `assert` guards in optional-dependency paths, and stale `__all__` module count references across documentation surfaces.

## Measurable Success Criteria

- All Python packages under `src/helping_hands/` declare `__all__` (45 total modules)
- Zero `Optional[X]` imports remain in source code (already satisfied — verified)
- `__all__` module count references updated across all doc surfaces (40 → 45)
- Error messages in `filesystem.py` include path context
- `assert` guards in `schedules.py` replaced with `RuntimeError`
- `ruff check .` and `ruff format --check .` pass cleanly
- All existing tests continue to pass (624 passed, 4 skipped)

## TODO

- [x] **T1 — Add `__all__` to 5 package `__init__.py` files**: `src/helping_hands/__init__.py`, `cli/__init__.py`, `lib/__init__.py`, `lib/hands/__init__.py`, `server/__init__.py`
- [x] **T2 — Server `__init__.py` already existed** — just added `__all__` declaration
- [x] **T3 — `Optional[X]`/`Union[X,Y]` already absent** — grep confirmed zero imports
- [x] **T4 — Improve error messages in `filesystem.py`** — `resolve_repo_target`, `read_text_file` now include path in ValueError/FileNotFoundError/IsADirectoryError
- [x] **T5 — Replace `assert` with `RuntimeError` in `schedules.py`** — 4 assert statements replaced with `if X is None: raise RuntimeError(...)` guarded by `# pragma: no cover`
- [x] **T6 — Update `__all__` module count** in AGENT.md, Architecture.md, Concepts.md, AGENT.md (Obsidian) from 40 → 45
- [x] **T7 — Run lint, format, and tests** — ruff check clean, ruff format clean, 624 passed / 4 skipped
- [x] **T8 — Reconcile Obsidian vault** — Completed PRDs index updated, project log entry added

## Non-Goals

- Adding new features or changing behavior
- Refactoring duplicate skill validation (already well-tested, not worth churn)
- Creating `.env.example` (would need user input on which vars to expose)
- Updating test count (already correct at 624)

## User Stories

- As a contributor, I want every package to declare `__all__` so IDE autocomplete and `from pkg import *` behave predictably.
- As a debugger, I want error messages to include the problematic path so I can identify issues quickly.
- As a reader of project docs, I want module counts to be accurate so I trust the documentation.

## Acceptance Criteria

1. `grep -r "from typing import Optional" src/` returns zero results — **PASS**
2. All 5 package `__init__.py` files declare `__all__` — **PASS** (45 total modules)
3. `ruff check .` exits 0 — **PASS**
4. `ruff format --check .` — **PASS** (70 files already formatted)
5. `uv run pytest` — **PASS** (624 passed, 4 skipped)
6. No `assert` used for optional-dependency guards in `schedules.py` — **PASS**

---

## Activity Log

- **2026-03-01** — PRD created after comprehensive audit of codebase. Identified 5 `__init__.py` files missing `__all__`, vague error messages in `filesystem.py`, 4 `assert` guards in `schedules.py`, and stale module count (40 → 45).
- **2026-03-01** — T1–T2: Added `__all__` to all 5 package `__init__.py` files.
- **2026-03-01** — T3: Verified — no `Optional`/`Union` imports exist in source.
- **2026-03-01** — T4: Enriched 4 error messages in `filesystem.py` with path context.
- **2026-03-01** — T5: Replaced 4 `assert` statements in `schedules.py` with `RuntimeError`.
- **2026-03-01** — T6: Updated `__all__` module count (40 → 45) across AGENT.md, Architecture.md, Concepts.md, Obsidian AGENT.md.
- **2026-03-01** — T7: Lint clean, format clean, 624 tests passed.
- **2026-03-01** — T8: Obsidian Completed PRDs index updated, project log entry added. PRD moved to `completed/`.
