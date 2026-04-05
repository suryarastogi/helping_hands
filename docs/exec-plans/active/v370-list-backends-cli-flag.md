# v370 — `--list-backends` CLI Flag

**Created:** 2026-04-05
**Status:** Active
**Theme:** CLI discoverability — let users see available backends and their status

## Context

Users have no CLI-native way to discover which backends are available, which
CLI tools are installed, and which Python extras are present. The `doctor`
command shows prerequisites but doesn't map them to backend names. A
`--list-backends` flag bridges this gap.

## Tasks

- [x] Add `list_backends()` function to `cli/main.py` that prints a table of all backends with availability status
- [x] Intercept `--list-backends` in `main()` before argparse (like `--version`)
- [x] Show CLI tool availability for CLI-backed hands, extra availability for library hands
- [x] Add tests for `list_backends()` output format and content
- [x] Add tests for `--list-backends` flag interception in `main()`
- [x] Update PLANS.md, INTENT.md, daily consolidation

## Completion criteria

- `helping-hands --list-backends` prints all backends with availability indicators
- Works without a positional `repo` argument
- All existing tests still pass
