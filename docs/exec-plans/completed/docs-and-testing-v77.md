# Execution Plan: Docs and Testing v77

**Status:** Completed
**Created:** 2026-03-06
**Goal:** Add E2E hand workflow design doc; extend docs structure validation tests (design doc source references, API docs completeness, PLANS.md structure, active/completed plan consistency).

---

## Tasks

### Phase 1: Documentation improvements

- [x] Add `e2e-hand-workflow.md` design doc (clone/branch/edit/commit/push/PR lifecycle, resume flow, dry-run, env config)
- [x] Update design-docs/index.md with new doc
- [x] Update docs/index.md design-docs listing

### Phase 2: Test improvements

- [x] Extend docs structure validation tests:
  - Design docs that reference `src/helping_hands/...` paths should point to real files
  - Design docs inter-linking other design docs should reference real files
  - API docs links in docs/index.md should resolve to existing files
  - API docs minimum file count verification
  - PLANS.md required sections (Active plans, Completed plans, How plans work)
  - Completed plan entries should include test counts
  - Active plans directory should not contain completed plans (status: Completed)
  - Design docs with "Key source files" sections should list real paths

### Phase 3: Finalize

- [x] All tests pass
- [x] Update PLANS.md
- [x] Update testing-methodology stats
- [x] Move plan to completed

---

## Completion criteria

- E2E hand workflow design doc covers clone, branch creation, edit, commit/push, PR create/resume, dry-run, and env config
- Extended docs validation tests catch drift in design doc source references, API docs listing, PLANS.md structure, and plan consistency
- All tests pass
- PLANS.md updated
