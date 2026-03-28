# v333 — DevinCLIHand & Factory Coverage Hardening

**Status:** in-progress
**Created:** 2026-03-28

## Goal

Close testable coverage gaps in `DevinCLIHand` (62% → ~95%) and
`factory.py` `get_enabled_backends()` (82% → ~95%). These are the two
non-server modules with the lowest coverage percentages.

## Tasks

- [x] Add tests for `DevinCLIHand._inject_prompt_argument` (3 tests)
- [x] Add tests for `DevinCLIHand._normalize_base_command` (3 tests)
- [x] Add tests for `DevinCLIHand._native_cli_auth_env_names` (1 test)
- [x] Add tests for `DevinCLIHand._describe_auth` (3 tests: native, key set, key unset)
- [x] Add tests for `DevinCLIHand._permission_mode` (3 tests: default, env override, empty)
- [x] Add tests for `DevinCLIHand._apply_backend_defaults` (5 tests: inject, preserve, non-devin, empty, env)
- [x] Add tests for `get_enabled_backends()` (8 tests: no env, sorted, single, multiple, falsy, mixed, truthy values, whitespace)
- [x] Update 2026-03-28 consolidation with v332
- [x] Run full test suite, verify ≥75% coverage gate
- [x] Update INTENT.md, PLANS.md

## Results

- 15 new DevinCLIHand tests (35 total, up from 20)
- 8 new `get_enabled_backends` tests (58 factory tests total, up from 50)
- 6485 backend tests passed, 0 failures, 75.87% coverage
- All doc structure tests pass

## Completion criteria

- DevinCLIHand coverage ≥ 90% ✓
- factory.py coverage ≥ 90% ✓
- All existing tests still pass ✓ (6485 passed)
- Docs updated ✓
