# v351 — Core Utility Module Test Coverage

**Created:** 2026-04-04
**Status:** Active

## Goal

Add test coverage for three 0%-covered pure utility modules: `validation.py`,
`github_url.py`, and `factory.py`. These are self-contained, have no
infrastructure dependencies, and are foundational to the codebase.

## Tasks

- [x] Move completed v350 plan from `active/` to `completed/2026/`
- [x] Update INTENT.md: move v350 to recently completed, add v351
- [x] Update PLANS.md: move v350 to completed, add v351
- [x] Add `TestHasCliFlag` and `TestInstallHint` to `test_validation.py`:
      7 new tests covering bare flag, equals form, absent flag, empty tokens,
      partial match rejection, single-dash rejection, and install_hint output
- [x] Add `TestInvalidRepoMsg`, `TestResolveGithubToken`, `TestRepoTmpDir`
      to `test_github_url.py`: 15 new tests covering token resolution
      (explicit, env, fallback, priority, whitespace), repo_tmp_dir (unset,
      set, nested creation, whitespace), invalid_repo_msg format
- [x] Add `test_factory.py`: 24 tests covering `__all__`, `SUPPORTED_BACKENDS`,
      `get_enabled_backends` (all-enabled default, sorted, single, truthy
      values 1/true/yes/on, falsy exclusion, multiple), `create_hand` (all
      11 backend dispatch branches + unknown backend error + max_iterations)
- [x] Run pytest, ruff check, ruff format — all clean (149 tests pass)
- [x] No untestable branches found — all three modules at 100% coverage

## Completion criteria

- validation.py 100% coverage ✓
- github_url.py 100% coverage ✓
- factory.py 100% coverage ✓ (exceeded ≥ 95% target)
- All new tests pass ✓
- ruff check + format clean ✓
