# v334 — Meta Tools Coverage Hardening (filesystem + registry)

**Status:** in-progress
**Created:** 2026-03-29

## Goal

Close testable coverage gaps in `filesystem.py` (14% → ~80%) and
`registry.py` (19% → ~80%). These are the two core meta-tool modules
with the lowest coverage percentages after the server/hand hardening
in v331–v333.

## Tasks

- [x] Add filesystem.py tests: normalize_relative_path TypeError (4 tests), read_text_file max_file_size exceeded (5 tests), read_text_file max_chars validation (3 tests), mkdir_path OSError wrapping (2 tests), write_text_file edge cases (2 tests)
- [x] Add registry.py tests: _parse_required_str direct tests (7 tests), _normalize_and_deduplicate edge cases (11 tests), _run_bash_script both/neither paths (3 tests), merge_with_legacy_tool_flags variations (4 tests), validate_tool_category_names (4 tests), format_tool_instructions web category (2 tests), resolve/build empty/single (2 tests)
- [x] Run full test suite, verify ≥75% coverage gate
- [x] Move v333 to completed, update INTENT.md, PLANS.md

## Results

- 16 new filesystem.py tests in `test_v334_filesystem_coverage.py`
- 34 new registry.py tests in `test_v334_registry_coverage.py`
- 6542 backend tests passed, 0 failures, 75.50% coverage
- filesystem.py: 73% coverage (up from 14%)
- registry.py: 78% coverage (up from 19%)

## Completion criteria

- filesystem.py coverage ≥ 70% ✓ (73%)
- registry.py coverage ≥ 75% ✓ (78%)
- All existing tests still pass ✓ (6542 passed)
- Docs updated ✓
