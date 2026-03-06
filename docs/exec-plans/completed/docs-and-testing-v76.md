# Execution Plan: Docs and Testing v76

**Status:** Completed
**Created:** 2026-03-06
**Goal:** Add model-resolution design doc; extend docs structure validation tests (PLANS.md link resolution, design-docs count sync in docs/index.md, tech-debt-tracker structure, TODO.md structure).

---

## Tasks

### Phase 1: Documentation improvements

- [x] Add `model-resolution.md` design doc (HandModel, provider inference, slash parsing, LangChain/Atomic adapters)
- [x] Update design-docs/index.md with new doc
- [x] Update docs/index.md design-docs listing

### Phase 2: Test improvements

- [x] Extend docs structure validation tests:
  - PLANS.md completed plan links resolve to actual files
  - docs/index.md design-docs parenthetical count matches actual files
  - Tech-debt-tracker has valid table structure with known priority values
  - TODO.md exists and has list items
  - Completed plans are non-trivial (minimum content length)
  - Design-docs index link count stays in sync (already exists, verify)

### Phase 3: Finalize

- [x] All tests pass
- [x] Update PLANS.md
- [x] Update testing-methodology stats
- [x] Move plan to completed

---

## Completion criteria

- Model-resolution design doc covers HandModel dataclass, resolve_hand_model flow, provider inference heuristics, and LangChain/Atomic adapter patterns
- Extended docs validation tests catch drift in PLANS.md links, docs/index.md design-docs listing, tech-debt-tracker structure, and TODO.md
- All tests pass
- PLANS.md updated
