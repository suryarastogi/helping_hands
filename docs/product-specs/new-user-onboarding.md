# Product Spec: New User Onboarding

**Status:** Mostly implemented (only nice-to-have #4 remaining)
**Created:** 2026-03-04
**Updated:** 2026-03-30

## User story

As a developer discovering helping_hands for the first time, I want a clear
path from installation to my first successful AI-driven code change so that I
can evaluate whether the tool fits my workflow.

## Current state

- README covers installation (`uv sync`) and a one-liner CLI example.
- No guided walkthrough, no sample repository, no "hello world" task.
- Users must already have a `GITHUB_TOKEN` and an AI provider key configured.

## Requirements

### Must have

1. **Quick-start section in README** — ~~three numbered steps: install, set keys,
   run a trivial task against a local directory.~~ **Implemented** (v346,
   2026-03-30): README Quick Start rewritten as three numbered steps
   (install → set API keys → run first task) with references to `doctor`
   and `examples/fix-greeting/`.
2. **`examples/` directory** ~~with at least one minimal sample repo (e.g. a tiny
   Python package with a deliberate bug) and a script that runs helping_hands
   against it.~~ **Implemented** (v345, 2026-03-30): `examples/fix-greeting/`
   contains a tiny Python package with a deliberate bug in `greet()` and a
   `run.sh` script that runs `helping-hands` with `--no-pr`.
3. **Environment checklist** — ~~a CLI command (`helping-hands doctor` or similar)
   that verifies required env vars and dependencies are present and reports
   what's missing.~~ **Implemented** (v344, 2026-03-30): `helping-hands doctor`
   checks Python version, git, uv, provider API keys, GitHub token, optional
   CLI backends, and optional extras. **Enhanced** (v347, 2026-04-04): added
   Docker availability check (for docker-sandbox backends) and Node.js
   version check (for frontend development).

### Nice to have

4. **Interactive mode** — if no `--prompt` is provided, prompt the user
   interactively for a task description.
5. **First-run banner** — ~~on first invocation, print a short welcome message
   with a link to the quick-start guide.~~ **Implemented** (v346, 2026-03-30):
   `_maybe_show_first_run_banner()` in `cli/main.py` prints a welcome message
   on first invocation, tracked via `~/.helping_hands/.first_run_done` marker.

## Acceptance criteria

- A new user can go from `git clone` to a successful local run in under
  5 minutes following only the quick-start steps.
- `helping-hands doctor` exits 0 when all dependencies and env vars are set,
  exits 1 otherwise with actionable messages.
- The example repo + script work on macOS and Linux with Python 3.12+.

## Design notes

- The `doctor` command should live in `cli/main.py` as a new subcommand,
  reusing `Config` validation logic where possible.
- The example script should use `--no-pr` to avoid requiring GitHub access
  for first evaluation.
