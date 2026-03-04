# Execution Plan: Improve Docs and Testing

**Status:** Active
**Created:** 2026-03-04
**Goal:** Establish the docs directory structure, add missing documentation scaffolding, and fill testing gaps for untested modules.

---

## Tasks

### Phase 1: Documentation structure (this session)

- [x] Create docs directory layout matching target structure:
  - `docs/design-docs/`, `docs/exec-plans/active|completed/`, `docs/generated/`,
    `docs/product-specs/`, `docs/references/`
- [x] Create `AGENTS.md` — multi-agent coordination guide
- [x] Create `ARCHITECTURE.md` — system architecture overview
- [x] Create `docs/DESIGN.md` — design philosophy and patterns
- [x] Create `docs/SECURITY.md` — security considerations
- [x] Create `docs/RELIABILITY.md` — reliability and error handling
- [x] Create `docs/QUALITY_SCORE.md` — quality metrics and standards
- [x] Create `docs/PLANS.md` — plans index
- [x] Create `docs/PRODUCT_SENSE.md` — product direction
- [x] Create `docs/FRONTEND.md` — frontend architecture
- [x] Create `docs/design-docs/index.md` — design docs index
- [x] Create `docs/design-docs/core-beliefs.md` — core design beliefs
- [x] Create `docs/product-specs/index.md` — product specs index
- [x] Create `docs/exec-plans/tech-debt-tracker.md` — tech debt tracking

### Phase 2: Testing improvements (this session)

- [x] Add `tests/test_filesystem.py` — tests for `lib/meta/tools/filesystem.py`
  (path normalization, traversal prevention, read/write/mkdir/exists)
- [x] Add `tests/test_default_prompts.py` — tests for `lib/default_prompts.py`
- [x] Verify all tests pass with `uv run pytest -v`

### Phase 3: Future improvements (next sessions)

- [ ] Add `docs/generated/db-schema.md` — auto-generated from models
- [ ] Add reference docs in `docs/references/` (uv-llms.txt, etc.)
- [ ] Expand product specs with detailed feature specs
- [ ] Add integration test coverage for CLI hand subprocess wrappers
- [ ] Add test coverage for `server/schedules.py` edge cases

---

## Completion criteria

- All Phase 1 and Phase 2 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check .` passes
