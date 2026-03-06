# Execution Plan: Docs and Testing v67

**Status:** Completed
**Created:** 2026-03-06
**Goal:** Add repo-indexing design doc; shared GitHub mock conftest fixture; package-level __init__.py tests for untested packages.

---

## Tasks

### Phase 1: Documentation improvements

- [x]Add `repo-indexing.md` design doc (RepoIndex, tree walking, .git exclusion, from_path pattern)
- [x]Update design-docs/index.md with new doc

### Phase 2: Test infrastructure

- [x]Add `mock_github_client` fixture to conftest.py (reduce repeated MagicMock setup across test_hand.py, test_hand_base_statics.py, test_e2e_hand_run.py, test_cli_hand_base_ci_loop.py)

### Phase 3: Package __init__.py tests

- [x]Add test_package_exports.py with tests for top-level `helping_hands`, `helping_hands.lib`, `helping_hands.cli`, `helping_hands.server`, `helping_hands.lib.hands` package re-exports and docstrings

### Phase 4: Finalize

- [x]All tests pass (1540 passed, 6 skipped)
- [x]Update QUALITY_SCORE.md
- [x]Update PLANS.md
- [x]Move plan to completed

---

## Completion criteria

- Repo-indexing design doc captures tree walking, .git exclusion, from_path pattern
- Shared GitHub mock fixture reduces boilerplate in 4+ test files
- All 5 untested package __init__.py files have dedicated tests
- All tests pass
- PLANS.md updated
