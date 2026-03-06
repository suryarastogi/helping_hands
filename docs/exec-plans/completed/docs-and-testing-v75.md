# Execution Plan: Docs and Testing v75

**Status:** Completed
**Created:** 2026-03-06
**Goal:** Add filesystem-security design doc; extend docs structure validation tests (FRONTEND.md sections, PRODUCT_SENSE.md sections, SECURITY.md sandboxing subsections, design doc minimum content checks).

---

## Tasks

### Phase 1: Documentation improvements

- [x] Add `filesystem-security.md` design doc (path confinement, resolve_repo_target, MCP sharing, sandboxing boundaries)
- [x] Update design-docs/index.md with new doc
- [x] Update docs/index.md design-docs listing

### Phase 2: Test improvements

- [x] Extend docs structure validation tests:
  - FRONTEND.md has required sections (Inline HTML UI, React frontend, Component structure)
  - PRODUCT_SENSE.md has required sections (What helping_hands is, Target users, Key value propositions, Product priorities)
  - SECURITY.md has sandboxing subsections (Codex CLI sandbox modes, Claude Code permissions, Container isolation)
  - Design docs are non-trivial (each .md file has minimum content length)
  - ARCHITECTURE.md has minimum section count
- [x] All tests pass (1656 pass, 8 skipped)

### Phase 3: Finalize

- [x] Update PLANS.md
- [x] Update testing-methodology stats
- [x] Move plan to completed

---

## Completion criteria

- Filesystem-security design doc covers path confinement, resolve_repo_target flow, MCP sharing, and sandboxing boundaries
- Extended docs validation tests catch structural drift in FRONTEND.md, PRODUCT_SENSE.md, SECURITY.md sandboxing, and design doc content
- All tests pass
- PLANS.md updated
