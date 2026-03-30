# v345 — Examples Directory & New User Onboarding

**Status:** Completed
**Created:** 2026-03-30

## Goal

Implement the `examples/` directory from the New User Onboarding product spec
(must-have item #2). Provide a minimal sample repo with a deliberate bug and a
script that runs helping_hands against it using `--no-pr` for local-only
evaluation.

## Tasks

- [x] Create `examples/fix-greeting/` — tiny Python package with a greeting
  function that has a deliberate bug (wrong return value)
- [x] Create `examples/fix-greeting/run.sh` — shell script that invokes
  `helping-hands` against the sample repo with `--no-pr`
- [x] Create `examples/README.md` — index of available examples
- [x] Add test: `main()` doctor early-return path (line 340) via patching
  the local `doctor` function
- [x] Add 5 tests for `examples/` directory structure
- [x] Update product spec status
- [x] Update INTENT.md with active → completed

## Completion criteria

- `examples/fix-greeting/` exists with `src/greet.py` (bugged), `tests/test_greet.py`,
  `run.sh` (executable), and `README.md`
- `examples/README.md` indexes available examples
- `cli/main.py` line 340 is covered by tests
- Product spec updated to reflect implementation
- All tests pass, coverage >= 76%

## Non-goals

- Interactive mode (nice-to-have #4 in product spec)
- First-run banner (nice-to-have #5 in product spec)
