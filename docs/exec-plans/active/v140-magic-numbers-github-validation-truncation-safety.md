## v140 — Extract remaining magic numbers, GitHub PR number validation, truncation limit safety

**Status:** Active
**Created:** 2026-03-12

## Goal

Three self-contained improvements continuing the hardening pattern:

1. **Extract remaining magic numbers** — `limit=2000` in `cli/base.py` `_build_apply_changes_prompt()`, `1024` byte read buffer in `cli/base.py` and `docker_sandbox_claude.py`, and `max_tokens=1024` default in `anthropic.py`. Extract to module-level constants `_APPLY_CHANGES_TRUNCATION_LIMIT`, `_STREAM_READ_BUFFER_SIZE`, and `_DEFAULT_MAX_TOKENS`.

2. **GitHub PR number/limit validation** — `get_pr(number)`, `update_pr_body(number)`, and `list_prs(limit)` in `github.py` don't validate their numeric parameters. Negative or zero values produce confusing PyGithub errors. Add explicit `ValueError` guards.

3. **`_truncate_diff` limit validation** — `_truncate_diff(limit)` in `pr_description.py` accepts zero/negative limits without error. Add `limit > 0` guard with `ValueError`.

## Tasks

- [x] Extract `_APPLY_CHANGES_TRUNCATION_LIMIT = 2000` in `cli/base.py`
- [x] Extract `_STREAM_READ_BUFFER_SIZE = 1024` in `cli/base.py` and `docker_sandbox_claude.py`
- [x] Extract `_DEFAULT_MAX_TOKENS = 1024` in `anthropic.py`
- [x] Add `number > 0` validation in `get_pr()` and `update_pr_body()` in `github.py`
- [x] Add `limit > 0` validation in `list_prs()` in `github.py`
- [x] Add `limit > 0` validation in `_truncate_diff()` in `pr_description.py`
- [x] Add tests for all improvements
- [x] Run lint and tests
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass
- `ruff check` and `ruff format` pass
- Docs updated with v140 notes
