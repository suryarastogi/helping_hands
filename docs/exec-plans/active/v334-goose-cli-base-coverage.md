# v334 — GooseCLIHand & CLIHandBase Coverage Hardening

**Status:** completed
**Created:** 2026-03-29

## Goal

Close testable coverage gaps in `GooseCLIHand` (88% → ~99%) and
`CLIHandBase` (98% → ~99%). These are the two CLI hand modules with
remaining uncovered branches.

## Tasks

- [x] Add tests for `GooseCLIHand._read_goose_config` yaml ImportError fallback
- [x] Add tests for `GooseCLIHand._read_goose_config` YAML parse exception
- [x] Add tests for `GooseCLIHand._read_goose_config` non-dict YAML data
- [x] Add tests for `GooseCLIHand._read_goose_config` successful provider+model read
- [x] Add tests for `GooseCLIHand._read_goose_config` model-only read
- [x] Add tests for `GooseCLIHand._read_goose_config` empty config keys
- [x] Add tests for `GooseCLIHand._read_goose_config` config file not found
- [x] Add tests for `GooseCLIHand._resolve_goose_provider_model_from_config` config file fallback
- [x] Add tests for `GooseCLIHand._resolve_goose_provider_model_from_config` empty provider with model inference
- [x] Add tests for `GooseCLIHand._resolve_goose_provider_model_from_config` unknown model infers openai
- [x] Add tests for `CLIHandBase._repo_has_changes` HEAD advance detection
- [x] Add tests for `CLIHandBase._repo_has_changes` HEAD same as baseline
- [x] Add tests for `CLIHandBase._has_pending_changes` delegation
- [x] Add tests for `CLIHandBase._fetch_failed_check_logs` subprocess timeout
- [x] Add tests for `CLIHandBase._fetch_failed_check_logs` FileNotFoundError
- [x] Add tests for `CLIHandBase._fetch_failed_check_logs` max_lines truncation
- [x] Add tests for `CLIHandBase._fetch_failed_check_logs` missing run_id in URL
- [x] Run full test suite, verify ≥75% coverage gate
- [x] Update INTENT.md, PLANS.md

## Results

- 10 new GooseCLIHand tests: 8 `_read_goose_config` + 3 config file fallback
- 7 new CLIHandBase tests: 2 HEAD advance, 2 `_has_pending_changes`, 4 `_fetch_failed_check_logs`
- GooseCLIHand coverage: 88% → 99% ✓
- CLIHandBase coverage: 98% → 99% ✓
- 6510 backend tests passed, 0 failures, 75.97% coverage ✓
- Docs updated ✓

## Completion criteria

- GooseCLIHand coverage ≥ 95% ✓ (99%)
- CLIHandBase coverage ≥ 99% ✓ (99%)
- All existing tests still pass ✓ (6510 passed)
- Docs updated ✓
