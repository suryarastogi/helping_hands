# Execution Plan: Docs and Testing v79

**Status:** Completed
**Created:** 2026-03-06
**Goal:** Add web-tools design doc; extend docs structure validation tests (RELIABILITY.md subsections, DESIGN.md content validation, conftest fixture self-tests, design doc cross-references).

---

## Tasks

### Phase 1: Documentation improvements

- [x] Add `web-tools.md` design doc (DuckDuckGo search, URL browsing, HTML extraction, content truncation, dataclasses)
- [x] Update design-docs/index.md with new doc
- [x] Update docs/index.md design-docs listing

### Phase 2: Test improvements

- [x] Extend docs structure validation tests:
  - RELIABILITY.md has expected subsections (error handling patterns, CLI subprocess failures, iterative hand failures, finalization failures, Docker sandbox failures, async compatibility fallbacks, heartbeat monitoring, idempotency)
  - RELIABILITY.md CLI subprocess failures has numbered items
  - DESIGN.md has expected subsections (guiding principles, patterns, hand abstraction, provider resolution, two-phase CLI hands, meta tools layer, finalization, error recovery patterns, testing patterns)
  - DESIGN.md guiding principles count validation
  - DESIGN.md error recovery table row count validation
  - Design docs have minimum content length (>= 500 chars, not stub files)
  - Design docs have at least two ## headings (structured content)
  - ARCHITECTURE.md references hand types (E2EHand, BasicLangGraphHand, BasicAtomicHand)
  - conftest.py fixtures are each referenced in at least one test file
  - Testing methodology doc has coverage targets, key patterns, and anti-patterns sections
  - Testing methodology doc references monkeypatch and importorskip

### Phase 3: Finalize

- [x] All tests pass (1717 passed)
- [x] Update PLANS.md
- [x] Update testing-methodology stats
- [x] Move plan to completed

---

## Completion criteria

- Web tools design doc covers DuckDuckGo integration, URL browsing, HTML stripping, content truncation, and dataclass design
- Extended docs validation tests catch drift in RELIABILITY/DESIGN doc sections, design doc content quality, and conftest fixture usage
- All tests pass
- PLANS.md updated
