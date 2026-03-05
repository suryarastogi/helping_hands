# Execution Plan: Improve Docs and Testing

**Status:** Completed
**Created:** 2026-03-04
**Completed:** 2026-03-04
**Goal:** Establish the docs directory structure, add missing documentation scaffolding, and fill testing gaps for untested modules.

---

## Tasks

### Phase 1: Documentation structure

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

### Phase 2: Testing improvements

- [x] Add `tests/test_filesystem.py` — tests for `lib/meta/tools/filesystem.py`
  (path normalization, traversal prevention, read/write/mkdir/exists)
- [x] Add `tests/test_default_prompts.py` — tests for `lib/default_prompts.py`
- [x] Verify all tests pass with `uv run pytest -v`

### Phase 3: Expanded testing and documentation

- [x] Expand `tests/test_repo.py` — 13 tests covering empty dirs, sort order,
  .git exclusion, .github inclusion, deeply nested files, error cases, dataclass defaults
- [x] Expand `tests/test_schedules.py` — added `TestNextRunTime`, `TestCronPresets`,
  roundtrip serialization, minimal from_dict, edge cases for cron validation
- [x] Expand `tests/test_task_result.py` — added tests for string, list, bool, empty dict,
  nested dict, custom exceptions, empty messages, status passthrough
- [x] Add `docs/generated/db-schema.md` — schema reference for ScheduledTask,
  TaskResult, RepoIndex, and Redis key patterns
- [x] Add `docs/references/uv-llms.txt` — uv package manager reference
- [x] Add `docs/references/ruff-llms.txt` — ruff linter/formatter reference
- [x] Add `docs/references/celery-redbeat-llms.txt` — RedBeat scheduler reference
- [x] Verify all 50 tests pass, lint clean

---

## Completion criteria

- All Phase 1, Phase 2, and Phase 3 tasks checked off
- `uv run pytest -v` passes (50 tests)
- `uv run ruff check .` passes
