# v346 — Quick Start Enhancement & First-Run Welcome Banner

**Status:** Completed
**Created:** 2026-03-30
**Completed:** 2026-03-30

## Goal

Complete New User Onboarding product spec must-have #1 (Quick Start section in
README with three numbered steps) and nice-to-have #5 (first-run welcome banner
on first CLI invocation).

## Tasks

- [x] Rewrite README Quick Start with three numbered steps
- [x] Add first-run welcome banner (`_maybe_show_first_run_banner()`)
- [x] Add tests for first-run banner
- [x] Update product spec status

## Changes

### README Quick Start rewrite

Replaced the wall-of-commands Quick Start with three clear numbered steps:

1. **Install** — `git clone`, `uv sync --dev`
2. **Set API keys** — export provider keys, verify with `helping-hands doctor`
3. **Run your first task** — try `examples/fix-greeting/run.sh` or point at a
   local repo with `--no-pr`

Detailed backend examples moved to a "More examples" subsection.

### First-run welcome banner

Added `_maybe_show_first_run_banner()` in `cli/main.py`:

- Prints a short welcome message on the very first CLI invocation
- Tracks state via `~/.helping_hands/.first_run_done` marker file
- Silently swallows filesystem errors (permission denied, read-only HOME)
- Called at the top of `main()` before subcommand dispatch

### Tests

5 new tests in `tests/test_cli_first_run_banner.py`:

- `test_shows_banner_on_first_run` — banner printed, marker created
- `test_suppressed_on_subsequent_run` — no output when marker exists
- `test_creates_parent_directory` — nested dir created automatically
- `test_returns_false_on_permission_error` — OSError on `exists()` handled
- `test_returns_false_on_write_error` — OSError on `write_text()` handled

### Product spec updates

Marked must-have #1 and nice-to-have #5 as implemented in
`docs/product-specs/new-user-onboarding.md`. Status updated to
"Mostly implemented (only nice-to-have #4 remaining)".

## Files changed

- `README.md` — Quick Start rewrite
- `src/helping_hands/cli/main.py` — `_maybe_show_first_run_banner()` + constants
- `tests/test_cli_first_run_banner.py` — 5 new tests
- `docs/product-specs/new-user-onboarding.md` — spec status updates
