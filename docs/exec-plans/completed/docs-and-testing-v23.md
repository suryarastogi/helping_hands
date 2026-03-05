# Execution Plan: Docs and Testing v23

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Fix schedule test collection errors, add unit tests for AtomicHand/LangGraphHand/GooseCLIHand uncovered methods; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: Fix schedule test collection errors

- [x] Add `pytest.importorskip("celery")` guards to `test_schedule_manager.py` and `test_schedules.py` so they skip cleanly when celery extra is not installed

### Phase 2: AtomicHand unit tests

- [x] `_build_agent` — mock `atomic_agents` imports, verify agent construction
- [x] `run()` — mock agent.run, verify HandResponse structure and finalization
- [x] `stream()` — AssertionError fallback path (sync fallback), async iterator path, non-async-iterable awaitable path

### Phase 3: LangGraphHand unit tests

- [x] `_build_agent` — mock `langgraph.prebuilt.create_react_agent`, verify construction
- [x] `run()` — mock agent.invoke, verify HandResponse structure
- [x] `stream()` — mock astream_events, verify chunk extraction and PR metadata yield

### Phase 4: GooseCLIHand additional tests

- [x] `_describe_auth` — provider env var presence/absence
- [x] `_normalize_base_command` — all 4 branches (bare goose, goose run, goose run --instructions, passthrough)
- [x] `_pr_description_cmd` — anthropic with claude available, anthropic without claude, non-anthropic

### Phase 5: Validation

- [x] All tests pass
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Update `docs/PLANS.md`
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-5 tasks checked off
- `uv run pytest -v` passes (no collection errors)
- `uv run ruff check . && uv run ruff format --check .` passes
