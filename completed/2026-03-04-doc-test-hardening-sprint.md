# PRD: Documentation & Test Hardening Sprint

**Status:** Completed
**Created:** 2026-03-04
**Completed:** 2026-03-04
**Goal:** Close documentation gaps, add missing test coverage for untested modules, and synchronize all doc surfaces (README, AGENT.md, Obsidian vault, MkDocs, TODO.md).

---

## Context

The codebase has grown significantly with five CLI backends (codex, claude, goose, gemini, opencode), a tool registry system, scheduling, and dual frontends. Documentation has not kept pace — Obsidian notes reference stale backend lists, TODO.md marks completed work as pending, key modules lack docstrings, and `opencode.py` has zero test coverage.

---

## TODO

### 1. Add OpenCodeCLIHand tests (CRITICAL)
- [x] Create `TestOpenCodeCLIHand` test class in `tests/test_hand.py`
- [x] Test: CLI command construction and model passthrough
- [x] Test: authentication failure message formatting
- [x] Test: subprocess env configuration
- [x] Test: run/stream basic flow (mocked subprocess)
- **Result:** 10 tests added. Coverage: 94% on `opencode.py`.

### 2. Add docstrings to iterative.py public/important methods
- [x] `run()` and `stream()` on `BasicLangGraphHand` and `BasicAtomicHand`
- [x] `_build_iteration_prompt()`
- [x] `_apply_inline_edits()` and `_extract_inline_edits()`
- [x] `_build_bootstrap_context()` and `_build_tree_snapshot()`
- [x] `_execute_tool_requests()` and `_extract_tool_requests()`
- [x] `_extract_read_requests()` and `_is_satisfied()`
- **Result:** ~15 Google-style docstrings added to key methods.

### 3. Add docstrings to e2e.py and langgraph.py public methods
- [x] `E2EHand.run()` and `E2EHand.stream()`
- [x] `LangGraphHand.run()`, `LangGraphHand.stream()`, `LangGraphHand.__init__()`, `LangGraphHand._build_agent()`
- **Result:** All public methods documented.

### 4. Add docstrings to server/app.py route handlers
- [x] Verified: all route handlers already have docstrings
- **Result:** No changes needed — initial audit was overly aggressive.

### 5. Update TODO.md — mark completed CLI backends
- [x] Mark Claude CLI, Gemini CLI, Goose CLI, OpenCode CLI as done
- [x] Mark backend selection/routing and streaming as done
- **Result:** 7 items changed from `[ ]` to `[x]`.

### 6. Update Obsidian Architecture.md
- [x] Add `goose`, `geminicli`, `opencodecli` to CLI and App mode backend lists
- [x] Add Goose CLI and OpenCode CLI backend requirements sections
- [x] Update data flow diagram with all backends
- [x] Obsidian AGENT.md already correctly points to root file (no sync needed)
- **Result:** Architecture.md fully reconciled with current codebase.

### 7. Add Obsidian Project Log entries for W09/W10
- [x] Created `2026-W09.md` (Feb 24 – Mar 2)
- [x] Created `2026-W10.md` (Mar 3 – Mar 9)
- [x] Updated Project Log.md latest pointer
- [x] Updated Weekly progress.md index
- **Result:** Three weeks of missing project log entries restored.

### 8. Update README.md last-updated date
- [x] Changed to "March 4, 2026"

### 9. Expand web.py tests
- [x] Test HTTP error status codes (403, 404)
- [x] Test network error propagation
- [x] Test content truncation edge cases
- [x] Test validation errors (empty query, bad URL, negative params)
- [x] Test URL deduplication
- [x] Test plain text handling
- [x] Test script/style tag stripping
- **Result:** 14 new tests added (4 → 18 total). Coverage: 92% (up from ~19%).

---

## Out of scope

- New feature development
- Frontend changes
- CI pipeline changes
- Refactoring hand implementations

---

## Activity Log

| Time | Action |
|------|--------|
| 2026-03-04 | PRD created after auditing docstrings, test gaps, and doc staleness |
| 2026-03-04 | TODO 1 complete: 10 OpenCodeCLIHand tests added (94% coverage) |
| 2026-03-04 | TODO 2 complete: ~15 docstrings added to iterative.py |
| 2026-03-04 | TODO 3 complete: docstrings added to e2e.py and langgraph.py public methods |
| 2026-03-04 | TODO 4 verified: all server/app.py routes already documented |
| 2026-03-04 | TODO 5 complete: TODO.md updated (7 items marked done) |
| 2026-03-04 | TODO 6 complete: Architecture.md reconciled with all 5 CLI backends |
| 2026-03-04 | TODO 7 complete: W09 and W10 project log entries created |
| 2026-03-04 | TODO 8 complete: README.md date updated to March 4, 2026 |
| 2026-03-04 | TODO 9 complete: 14 new web.py tests (92% coverage) |
| 2026-03-04 | All 293 tests passing. PRD moved to completed/ |
