# Execution Plan: Docs and Testing v71

**Status:** Completed
**Created:** 2026-03-06
**Goal:** Add skills-system design doc; extend docs structure validation tests (product-specs index completeness, root-level docs existence, tech-debt-tracker module references).

---

## Tasks

### Phase 1: Documentation improvements

- [x] Add `skills-system.md` design doc (catalog discovery, normalization, staging, CLI integration)
- [x] Update design-docs/index.md with new doc
- [x] Update docs/index.md design-docs listing

### Phase 2: Test improvements

- [x] Extend docs structure validation tests:
  - product-specs/index.md lists every .md file in product-specs/
  - Root-level docs (ARCHITECTURE.md, AGENTS.md, CLAUDE.md) exist
  - Tech-debt-tracker active items reference real source modules
  - References directory files are non-empty
- [x] All tests pass (1595 passed)

### Phase 3: Finalize

- [x] Update PLANS.md
- [x] Update testing-methodology stats
- [x] Move plan to completed

---

## Completion criteria

- Skills system design doc covers catalog structure, normalization, staging, and prompt injection
- Extended docs validation tests catch structural drift
- All tests pass
- PLANS.md updated
