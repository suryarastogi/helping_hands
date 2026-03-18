# v259: DRY _repo_tmp_dir, GitHub token resolution, truthy values

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Goal

Three self-contained DRY improvements:

1. **Extract `_repo_tmp_dir()`** — identical implementations in `cli/main.py:421`
   and `server/celery_app.py:154`. Move to `lib/github_url.py` as `repo_tmp_dir()`
   and import from both call sites.

2. **Extract GitHub token resolution** — `os.environ.get("GITHUB_TOKEN",
   os.environ.get("GH_TOKEN", ""))` duplicated in `lib/github.py:179-180` and
   `lib/github_url.py:79-80`. Add `resolve_github_token()` to `github_url.py`
   and call from both.

3. **Unify truthy values in `pr_description.py`** — inline `{"1", "true", "yes",
   "on"}` at line 205 should use `_TRUTHY_VALUES` from `config.py`. Define
   `_PR_TRUTHY_VALUES = _TRUTHY_VALUES | {"on"}` locally to avoid cross-layer
   import from cli to lib.

## Tasks

- [x] Create active plan
- [x] Add `repo_tmp_dir()` to `github_url.py`
- [x] Replace `_repo_tmp_dir()` in `cli/main.py` with import
- [x] Replace `_repo_tmp_dir()` in `server/celery_app.py` with import
- [x] Add `resolve_github_token()` to `github_url.py`
- [x] Use in `lib/github.py`
- [x] Use in `lib/github_url.py` (internal call)
- [x] Use `_TRUTHY_VALUES | {"on"}` in `pr_description.py`
- [x] Add tests for `repo_tmp_dir()`
- [x] Add tests for `resolve_github_token()`
- [x] Add tests for `_is_disabled()` truthy consistency
- [x] Run lint, type check, tests
- [x] Update docs

## Completion criteria

- All 3 duplicate patterns replaced with shared helpers
- No bare `"GITHUB_TOKEN"` / `"GH_TOKEN"` strings remain in `github.py` or `github_url.py`
- No inline truthy set remains in `pr_description.py`
- No duplicate `_repo_tmp_dir()` functions remain
- 32 new tests pass
- Full test suite passes

## Files touched

- `src/helping_hands/lib/github_url.py` (add 2 functions + 3 constants)
- `src/helping_hands/lib/github.py` (use `resolve_github_token`)
- `src/helping_hands/lib/hands/v1/hand/pr_description.py` (use `_TRUTHY_VALUES`)
- `src/helping_hands/cli/main.py` (import `repo_tmp_dir`, remove local copy)
- `src/helping_hands/server/celery_app.py` (import `repo_tmp_dir`, remove local copy)
- `tests/test_v259_dry_repo_tmp_token_resolution_truthy.py` (32 new tests)
