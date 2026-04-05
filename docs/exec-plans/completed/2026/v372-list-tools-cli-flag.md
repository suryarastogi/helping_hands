# v372 — `--list-tools` CLI Flag & Registry Coverage

**Status:** Completed
**Created:** 2026-04-05

## Goal

Add `--list-tools` CLI flag for tool category discoverability, complementing
the existing `--list-backends`. Close the last testable registry coverage gap
(line 255 — bash script both/neither provided).

## Tasks

- [x] `list_tools()` function in `cli/main.py` — format a table of all tool
  categories with their tool specs and descriptions.
- [x] `--list-tools` flag — intercepted before argparse (like `--version` and
  `--list-backends`) so it works without a positional `repo` argument.
- [x] Registry gap — add 2 tests for `_run_bash_script` both-provided and
  neither-provided error branches (line 255).
- [x] Tests — cover `list_tools()` output structure and `--list-tools` flag
  interception.
- [x] Docs — update INTENT.md, PLANS.md, daily consolidation.

## Completion criteria

- `helping-hands --list-tools` prints tool category table and exits 0.
- Registry coverage reaches 100%.
- All existing tests pass.
