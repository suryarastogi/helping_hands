# v99 - Docs and testing improvements

**Status:** complete
**Created:** 2026-03-07

## Tasks

- [x] Add dedicated `test_anthropic_provider.py` (class attrs, `_build_inner` with/without API key, `_complete_impl` delegation/kwargs/max_tokens default/custom, singleton identity; 13 tests)
- [x] Enhance `test_google_provider.py` with `_build_inner` tests (ImportError, with/without API key), class attrs, singleton identity (7 new tests)
- [x] Update `testing-methodology.md` coverage count (2883 -> 2905 tests)
- [x] Update `PLANS.md` to reference active plan
- [x] Update `QUALITY_SCORE.md` provider coverage notes

## Completion criteria

- [x] All new tests pass (2905 passed, 0 failed)
- [x] `uv run ruff check .` and `uv run ruff format --check .` pass
- [x] Coverage count updated in testing-methodology.md
- [x] PLANS.md references this plan
