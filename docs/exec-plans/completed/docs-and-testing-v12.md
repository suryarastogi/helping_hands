# Execution Plan: Docs and Testing v12

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add unit tests for registry runner wrappers (payload validation + mocked happy paths) and MCP server error paths (read_file error variants, _repo_root, _command_result_to_dict); fix UnicodeError handler ordering bug; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: Registry runner wrapper tests

- [x] `_run_python_code` — missing/invalid code, valid payload with mocked downstream
- [x] `_run_python_script` — missing/invalid script_path, valid payload with mocked downstream
- [x] `_run_bash_script` — invalid script_path/inline_script types, valid payload with mocked downstream
- [x] `_run_web_search` — missing/invalid query, valid payload with mocked downstream
- [x] `_run_web_browse` — missing/invalid url, valid payload with mocked downstream

### Phase 2: MCP server error path tests

- [x] `_repo_root` — non-existent path raises FileNotFoundError, file path raises FileNotFoundError
- [x] `_command_result_to_dict` — converts all fields (success, failure, timed_out)
- [x] `read_file` — IsADirectoryError path, UnicodeError path, path traversal ValueError
- [x] `write_file` — path traversal ValueError

### Phase 2b: Bug fix

- [x] Fix `read_file` exception handler ordering — `UnicodeError` (subclass of `ValueError`) was caught by `ValueError` handler first, making the `UnicodeError` handler dead code. Reordered to catch `UnicodeError` before `ValueError`.

### Phase 3: Validation

- [x] All tests pass (91 passed in related files)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Move plan to completed, update `docs/PLANS.md`

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
