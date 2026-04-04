# v352 — CLI Hand Test Coverage: OpenCode + Devin

**Created:** 2026-04-04
**Status:** Active

## Goal

Close test coverage gaps in `opencode.py` and `devin.py` CLI hand modules.
Both have untested methods (`_describe_auth`, `_pr_description_cmd`,
`_pr_description_prompt_as_arg`) and edge cases in model resolution that
are critical for correct provider routing and auth error reporting.

## Tasks

- [x] Move completed v351 plan from `active/` to `completed/2026/`
- [x] Add v351 to Week-14 consolidation
- [x] Add `TestDescribeAuth` to `test_cli_hand_opencode.py`:
      7 new tests covering provider/model with known provider (key set/unset),
      unknown provider, bare model (no slash), empty model, default model,
      google provider
- [x] Add `TestPrDescriptionCmd` to `test_cli_hand_opencode.py`:
      2 tests for opencode on PATH vs not on PATH
- [x] Add `TestPrDescriptionCmd` to `test_cli_hand_devin.py`:
      2 tests for devin on PATH vs not on PATH
- [x] Add `TestPrDescriptionPromptAsArg` to `test_cli_hand_devin.py`:
      1 test confirming returns True
- [x] Add `TestResolveCliModelEnvEdge` to `test_cli_hand_devin.py`:
      5 tests for env var "default" marker, "None" marker, whitespace-only,
      unset, and both-empty fallback
- [x] Run pytest, ruff check, ruff format — all clean (6744 tests pass)
- [x] Update INTENT.md, PLANS.md, Week-14 consolidation

## Completion criteria

- opencode.py `_describe_auth()` all branches covered ✓
- opencode.py `_pr_description_cmd()` both branches covered ✓
- devin.py `_pr_description_cmd()` both branches covered ✓
- devin.py `_pr_description_prompt_as_arg()` covered ✓
- devin.py `_resolve_cli_model` env var edge cases covered ✓
- All new tests pass ✓ (17 new tests, 6744 total pass)
- ruff check + format clean ✓
