# v365 — CLI `--version` Flag & Doctor Version Display

**Status:** Completed
**Created:** 2026-04-04

## Goal

Add `--version` / `-V` flag to the CLI and include the version in `doctor`
output header. The `__version__` constant is defined in `__init__.py` but is
not surfaced through any user-facing command.

## Tasks

- [x] Handle `--version`/`-V` before positional arg parsing in `main()`
- [x] Add version to `doctor` output header in `format_results()`
- [x] Add tests for `--version` flag (4 tests in `test_cli.py`)
- [x] Add test for doctor version header (1 test in `test_cli_doctor.py`)

## Completion criteria

- `helping-hands --version` and `helping-hands -V` print the version and exit
  without requiring a positional `repo` argument.
- `helping-hands doctor` output header includes the version string.
- Tests verify both behaviours and confirm the printed version matches
  `helping_hands.__version__`.

## Rationale

Users need a way to check which version they're running when reporting bugs
or verifying upgrades. The `doctor` command is the natural place to also
surface version info.
