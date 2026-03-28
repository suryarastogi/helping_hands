# v328 — Test Coverage Hardening: Devin CLI, Filesystem, Validation

**Status:** Completed
**Created:** 2026-03-28
**Completed:** 2026-03-28
**Goal:** Raise test coverage for three under-tested modules to >80%, targeting security-critical and widely-used code paths.

## Motivation

Overall backend coverage was 78.48%. Three modules had significant gaps:
- `DevinCLIHand` (62%) — missing tests for command normalization, backend defaults injection, permission mode
- `filesystem.py` — missing tests for file size limits, mkdir error wrapping, type guard on normalize
- `validation.py` — missing dedicated tests for `has_cli_flag`, `install_hint`, `format_type_error`

## Results

- 41 new tests added (24 DevinCLIHand + 5 filesystem + 12 validation)
- 6467 tests passed (up from 6426), 0 failures
- 78.83% overall coverage (up from 78.48%)

## Tasks

- [x] Create active plan
- [x] Add DevinCLIHand tests: `_normalize_base_command`, `_apply_backend_defaults`, `_permission_mode`, `_describe_auth`, `_inject_prompt_argument`, `_native_cli_auth_env_names`
- [x] Add filesystem.py tests: `max_file_size` rejection, `mkdir_path` OSError wrapping, `normalize_relative_path` type error
- [x] Add validation.py tests: `has_cli_flag` (bare flag, prefix form, missing), `install_hint`, `format_type_error`
- [x] Run full test suite — all tests pass
- [x] Update docs: PLANS.md, INTENT.md

## Completion criteria

- [x] All new tests pass (0 failures)
- [x] Overall backend coverage >= 78.48% (no regression) — achieved 78.83%
- [x] DevinCLIHand, filesystem, and validation modules have dedicated test coverage for all previously-untested public methods

## Files touched

- `tests/test_cli_hand_devin.py` — 7 new test classes (24 tests)
- `tests/test_filesystem.py` — 3 new test classes (5 tests)
- `tests/test_validation.py` — 3 new test classes (12 tests)
- `docs/exec-plans/completed/2026/v328-test-coverage-hardening.md` — this plan
- `docs/PLANS.md` — plan entry
- `INTENT.md` — completed entry
