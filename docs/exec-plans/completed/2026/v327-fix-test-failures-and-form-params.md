# v327 — Fix Test Failures & Form Param Gap

**Created:** 2026-03-28
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Fix 9 test failures from v325–v326 feature additions and close the form parameter gap for `issue_number`/`create_issue`.

## Context

v325 (issue linking) and v326 (issue creation) added `issue_number` and `create_issue`
fields to `BuildRequest` and the Celery task, but:

1. The inline HTML form endpoint `enqueue_build_form` was not updated with the new
   Form parameters — they silently default but are missing from the handler signature.
2. The 5 `TestBuildForm` tests don't include the new fields in their expected dicts.
3. Three completed plan files (v324–v326) don't conform to the plan structure tests
   (missing status metadata, using `## Plan` instead of `## Tasks`).
4. PLANS.md entries for v324–v326 use "N frontend tests" format instead of "N tests"
   and lack YYYY-MM-DD dates in link lines.

## Tasks

- [x] Create active execution plan
- [x] Fix v324 plan: add status metadata, rename `## Plan` → `## Tasks`
- [x] Fix v325 plan: add status metadata, rename `## Plan` → `## Tasks`
- [x] Fix v326 plan: rename `## Plan` → `## Tasks`
- [x] Fix PLANS.md v324–v326 entries: add dates, use "N tests" format
- [x] Add `issue_number`/`create_issue` Form params to `enqueue_build_form`
- [x] Update 5 `TestBuildForm` expected dicts with new fields
- [x] Run tests and verify all 9 failures resolved
- [x] Update docs, move plan to completed

## Completion criteria

- All `test_docs_structure.py` tests pass
- All `test_server_app.py::TestBuildForm` tests pass (when fastapi available)
- `enqueue_build_form` accepts `issue_number` and `create_issue` form fields
- No regressions in existing test suite

## Results

- **All 6426 tests pass**, 0 failures, 78.48% coverage (above 75% threshold)
- **Files changed:** `app.py` (form handler), `test_server_app.py` (5 assertions),
  `v324/*.md`, `v325/*.md`, `v326/*.md` (plan structure), `PLANS.md` (index)
- **9 test failures resolved:** 5 TestBuildForm + 4 TestDocsStructure
- **Bug fixed:** `enqueue_build_form` now accepts `issue_number` and `create_issue`
  form fields, making the inline HTML form feature-complete with the JSON API
