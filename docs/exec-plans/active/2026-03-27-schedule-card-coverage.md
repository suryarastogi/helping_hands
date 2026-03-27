# Execution Plan: ScheduleCard Form Field Test Coverage

**Created:** 2026-03-27
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Expand ScheduleCard test coverage from 0.50x to ~1.0x test-to-source ratio by testing all form field interactions, checkbox toggles, cron preset selection, advanced settings, and schedule item edge cases.

## Context

ScheduleCard had the lowest test-to-source ratio (0.50x) among frontend components. The existing 20 tests covered basic rendering and button callbacks but missed all form field `onChange` handlers in the `ScheduleFormFields` sub-component (cron, repo, prompt, backend, model, iterations, PR number, tools, skills, checkboxes, github token, reference repos) and the cron preset select behavior.

## Tasks

- [x] **Cron expression & preset select** — Test cron input onChange, preset select → onUpdateField("cron_expression", ...), preset matching display, empty preset "Custom" option. Tests added: 5
- [x] **Form field onChange handlers** — Test prompt textarea, backend select, model input, max_iterations input (with clamping), PR number input, tools input, skills input, github token input. Tests added: 10
- [x] **Checkbox toggles** — Test no_pr, enable_execution, enable_web, fix_ci, enabled checkboxes call onUpdateField with correct boolean. Tests added: 5
- [x] **Advanced settings details toggle** — Test that advanced fields are inside a `<details>` element. Tests added: 1
- [x] **Schedule item edge cases** — Test schedule without next_run_at/last_run_at, multiple schedules rendering, empty message hidden. Tests added: 4
- [x] **Reference repos chip integration** — Test that reference_repos string is parsed to chips and empty string renders no chips. Tests added: 2

## Completion criteria

- All task areas checked off
- All frontend tests pass with no regressions (1 pre-existing flaky WASD test excluded)
- ScheduleCard test file has 46 tests (up from 20)

## Results

- **ScheduleCard tests:** 20 → 46 (+26)
- **Frontend tests total:** 681 → 707 (+26)
- **Test-to-source ratio:** 0.50x → 1.08x
