# v347 — Fix test drift from README slim + validation coverage

**Created:** 2026-04-04
**Status:** Completed

## Objective

The recent README slimming (commit `c7601f0`) moved Configuration and Development
sections to dedicated docs, but the doc-structure tests still assert the old
README shape. Additionally, `docs/index.md` is missing references to some
top-level docs, grill tests lack skip guards for missing server extras, and
validation helpers need `has_cli_flag`/`install_hint` test coverage.

## Tasks

- [x] Update `TestReadmeMdSections` parametrize list (remove `## Configuration`/`## Development`, verify `## Documentation`)
- [x] Update `TestReadmeSections::test_mentions_github_token` → `test_has_documentation_section`
- [x] Add `app-mode.md`, `backends.md`, `development.md` to `docs/index.md`
- [x] Add `pytest.importorskip("celery")` to `test_grill.py`
- [x] Add `TestHasCliFlag` and `TestInstallHint` classes to `test_validation.py`
- [x] Add v347 reference to `PLANS.md`
- [x] Run full test suite — 7710 passed, 8 skipped, 91.33% coverage
- [x] Move plan to completed, update INTENT.md

## Results

- 17 previously failing tests now pass (4 doc-structure fixed, 13 grill properly skipped)
- 12 new validation tests added (`TestHasCliFlag`: 7 tests, `TestInstallHint`: 3 tests, plus `__all__` updated)
- `validation.py`: 100% line+branch coverage
- Overall coverage: 91.33% (with server extras), 7710 tests passed
