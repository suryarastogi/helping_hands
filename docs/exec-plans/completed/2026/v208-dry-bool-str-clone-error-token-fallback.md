# v208 — DRY bool-to-string, git clone error constants, GitHub token fallback

**Status:** Completed
**Created:** 2026-03-15

## Tasks

- [x] DRY `str(x).lower()` → `bool_str(x)` helper in `github_url.py` —
  Replace 13× `str(bool_val).lower()` across `celery_app.py`, `base.py`,
  `e2e.py`, `iterative.py`, `cli/base.py` with a shared `bool_str()` helper
- [x] DRY git clone error message — Extract `DEFAULT_GIT_CLONE_ERROR_MSG`
  constant in `github_url.py`, use it in `cli/main.py` and `celery_app.py`
  instead of inline `"unknown git clone error"` strings
- [x] DRY GitHub token fallback — Extract `resolve_github_token()` in
  `github_url.py`, use it in `github.py` `_authenticate()` and
  `build_clone_url()` instead of duplicated
  `os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN", ""))`
- [x] Add 21 new tests (20 passed, 1 skipped without fastapi)
- [x] Update 1 existing test (`__all__` exports)
- [x] Run quality gates — all pass

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
