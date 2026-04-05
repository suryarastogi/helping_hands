# v380 — Registry Coverage Completion & Runner Test Hardening

**Created:** 2026-04-05
**Status:** Active

## Goal

Close the last registry branch partial (line 560→558 in
`format_tool_instructions_for_cli`) and add dedicated tests for
`_parse_required_str`, which is used by 4 runner wrappers but has no
standalone validator test class. Add missing custom-params forwarding
tests for `_run_python_script` and `_run_bash_script`.

## Context

Registry module sits at 99% line coverage with 1 branch partial. The
`_parse_required_str` validator is tested indirectly through runner
wrappers (missing/empty/non-string rejection), but lacks a dedicated
test class for edge cases like `None` value, bool input, and integer
input. Runner wrapper tests for `_run_python_script` and
`_run_bash_script` are missing custom-params forwarding verification
(only defaults tested).

## Tasks

- [x] Create active plan v380
- [x] Add `TestParseRequiredStr` class to `test_registry_validators.py`
- [x] Add branch-partial test for `format_tool_instructions_for_cli` with unknown tool
- [x] Add custom-params test for `_run_python_script`
- [x] Add custom-params test for `_run_bash_script`
- [x] Move v379 to completed, update PLANS.md, INTENT.md, consolidation docs

## Completion criteria

- Registry coverage: 100% lines, 100% branches
- All new tests pass
- `_parse_required_str` has dedicated validator test class with ≥5 tests
- Runner custom-params forwarding verified for all 5 runners
- Docs updated with v380 entry

## Files changed

- `tests/test_registry_validators.py`
- `tests/test_registry_runners.py`
- `tests/test_registry_public_api.py`
- `docs/exec-plans/active/v380-registry-coverage-completion.md`
- `docs/PLANS.md`
- `INTENT.md`
- `docs/exec-plans/completed/2026/2026-04-05.md`
- `docs/exec-plans/completed/2026/Week-14.md`
