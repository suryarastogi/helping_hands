# v378 — MCP Bash Script Validation Tests & Plan Hygiene

**Status:** ✅ Complete
**Created:** 2026-04-05

## Goal

Close the last two uncovered lines in `server/mcp_server.py` (the `run_bash_script`
neither/both validation branches at lines 370, 372) and perform plan hygiene:
move completed v377 to completed/, add v377 entry to PLANS.md, update INTENT.md.

## Tasks

- [x] Move v377 from `exec-plans/active/` to `exec-plans/completed/2026/`
- [x] Fix INTENT.md v377 plan link
- [x] Add tests for `run_bash_script` neither-provided and both-provided errors
- [x] Add v377 + v378 entries to PLANS.md
- [x] Update INTENT.md with v378 entry
- [x] Update Week-14 consolidation with v377 + v378
- [x] Fix v377 completed plan missing `## Tasks` section
- [x] Fix v378 completion criteria casing
- [x] Verify all tests pass (0 failures)

## Completion criteria

- `server/mcp_server.py` reaches 100% line coverage (0 uncovered lines)
- All doc structure tests pass
- PLANS.md, INTENT.md, and Week-14 are up to date

## Tests

2 new tests in `tests/test_v378_mcp_bash_validation.py`:

- **Neither provided** (1): `run_bash_script(repo_path)` with no script_path or inline_script raises ValueError
- **Both provided** (1): `run_bash_script(repo_path, script_path="x", inline_script="y")` raises ValueError

**7018 total tests pass. 99.93% coverage.**
