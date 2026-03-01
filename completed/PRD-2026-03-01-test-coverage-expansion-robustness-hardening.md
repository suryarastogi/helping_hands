# PRD: Test Coverage Expansion & Robustness Hardening

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Close the three largest test coverage gaps (ScheduleManager, Celery helpers, skills payload validators), fix a validation gap in bash script skill payload, add missing MkDocs API page, and reconcile all documentation surfaces.

---

## Problem Statement

The helping_hands codebase has strong architecture and four completed PRDs worth of hardening, but a codebase audit reveals concrete remaining gaps:

1. **`ScheduleManager` has zero test coverage.** The `test_schedules.py` file only covers the `ScheduledTask` dataclass, `validate_cron_expression()`, and `generate_schedule_id()`. All 13 `ScheduleManager` methods (CRUD, enable/disable, record_run, trigger_now) are untested. This is the largest test coverage gap in the project.

2. **Celery app helper functions are partially tested.** `_redact_sensitive()`, `_repo_tmp_dir()`, `_github_clone_url()`, `_trim_updates()`, `_append_update()`, and `_UpdateCollector` lack tests. These are self-contained pure functions ideal for unit testing.

3. **Skills payload validator runners have no tests.** `_run_python_code()`, `_run_python_script()`, `_run_bash_script()`, `_run_web_search()`, and `_run_web_browse()` parse and validate user-provided payloads but have no test coverage for malformed inputs.

4. **`_run_bash_script()` accepts empty payloads.** Both `script_path` and `inline_script` can be `None`, which passes validation but produces a confusing downstream error from `command_tools.run_bash_script()`.

5. **`default_prompts.py` has no MkDocs API doc page.** The module exists in source but is invisible in the published docs site.

6. **Documentation surfaces need reconciliation.** Obsidian Project Log needs updating, `Project todos.md` needs sync, and README structure tree is missing `default_prompts.py`.

## Success Criteria

- [x] `test_schedules.py` has unit tests for all `ScheduleManager` methods using mocked Redis/RedBeat
- [x] `test_celery_app.py` has tests for `_redact_sensitive`, `_repo_tmp_dir`, `_github_clone_url`, `_trim_updates`, `_append_update`, `_UpdateCollector`
- [x] `test_meta_skills.py` has tests for skill payload runners with valid and malformed inputs
- [x] `_run_bash_script()` validates that at least one of `script_path`/`inline_script` is non-empty
- [x] `default_prompts.py` has an MkDocs API doc page and nav entry
- [x] Obsidian Project Log, Project todos, and README reconciled
- [x] All tests pass (449 passed)

## Non-Goals

- Adding integration tests (Redis, Celery broker required)
- Changing ScheduleManager behavior or architecture
- Adding new features or backends
- Rewriting existing prose in docs

---

## TODO

### 1. Add ScheduleManager unit tests with mocked Redis/RedBeat
- [x] Test `create_schedule()` — happy path, duplicate rejection, auto-ID generation, disabled skips RedBeat
- [x] Test `get_schedule()` — found, not found
- [x] Test `list_schedules()` — empty, multiple items, sorted by created_at
- [x] Test `update_schedule()` — happy path, not-found error, metadata preservation
- [x] Test `delete_schedule()` — found, not found
- [x] Test `enable_schedule()` / `disable_schedule()` — toggle behavior, noop when already in state, not-found
- [x] Test `record_run()` — updates metadata, increments run_count, noop for missing schedule
- [x] Test `trigger_now()` — triggers build_feature, records run, not-found returns None

### 2. Add Celery helper function tests
- [x] Test `_redact_sensitive()` — token redaction, no-match passthrough, multiple tokens
- [x] Test `_github_clone_url()` — with GITHUB_TOKEN, with GH_TOKEN fallback, without token
- [x] Test `_repo_tmp_dir()` — env set (creates dir), env empty, env missing
- [x] Test `_trim_updates()` — under limit, at limit, over limit trims oldest
- [x] Test `_append_update()` — normal, strips whitespace, empty ignored, truncation
- [x] Test `_UpdateCollector` — line splitting, partial buffering, flush, auto-flush on large chunks, empty noop

### 3. Add skills payload runner tests
- [x] Test `_run_python_code()` — missing code, non-string code, empty code, valid code, invalid/negative/bool timeout
- [x] Test `_run_python_script()` — missing script_path, non-string, empty, valid
- [x] Test `_run_bash_script()` — both None, both empty, non-string types, valid script_path, valid inline_script
- [x] Test `_run_web_search()` — missing query, non-string, empty, valid
- [x] Test `_run_web_browse()` — missing url, non-string, empty, valid
- [x] Test `_parse_str_list()` — valid, None, missing, non-list, non-string elements
- [x] Test `_parse_positive_int()` — default, provided, zero, bool
- [x] Test `_parse_optional_str()` — present, missing, empty, non-string

### 4. Fix `_run_bash_script()` validation gap
- [x] Add validation: at least one of `script_path`/`inline_script` must be non-empty string

### 5. Add missing MkDocs API page for `default_prompts.py`
- [x] Create `docs/api/lib/default_prompts.md`
- [x] Add to `mkdocs.yml` nav under lib

### 6. Reconcile documentation surfaces
- [x] Update Obsidian `Project Log/2026-W09.md` with this session's work
- [x] Sync `obsidian/docs/Project todos.md` design notes
- [x] Update `README.md` project structure tree (add `default_prompts.py`)
- [x] Update AGENT.md recurring decisions (skills payload validation)

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created; codebase audit identified test coverage, validation, and documentation gaps |
| 2026-03-01 | Added 22 ScheduleManager unit tests with mocked Redis/RedBeat (CRUD, enable/disable, record_run, trigger_now) |
| 2026-03-01 | Added 15 Celery helper function tests (_redact_sensitive, _github_clone_url, _repo_tmp_dir, _trim_updates, _append_update, _UpdateCollector) |
| 2026-03-01 | Added 30 skills payload runner validation tests + 12 parse helper tests |
| 2026-03-01 | Fixed `_run_bash_script()` to validate at least one of script_path/inline_script is non-empty |
| 2026-03-01 | Created `docs/api/lib/default_prompts.md` and added to `mkdocs.yml` nav |
| 2026-03-01 | Reconciled obsidian (Project Log W09, Project todos), README structure tree, AGENT.md recurring decisions |
| 2026-03-01 | All 449 tests pass; lint and format clean. PRD complete |
