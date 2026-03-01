# PRD: MCP/App Test Hardening, Internal Helper Tests, and Doc Reconciliation

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Expand test coverage for MCP server edge cases, server app internal helpers and failure paths, and reconcile documentation surfaces for the current work cycle.

---

## Problem Statement

After seven completed PRDs, the codebase has strong public API documentation and ~471 tests. However, a fresh audit reveals targeted improvement areas:

1. **MCP server test gaps** — `build_feature()` error paths (invalid skills), `_repo_root` missing-dir, `read_file` directory/unicode errors, `_command_result_to_dict` helper, and `main()` entry point lack tests.
2. **Server app internal helper tests** — `_parse_backend`, `_normalize_task_status`, `_extract_task_id`, `_extract_task_name`, `_extract_task_kwargs`, `_coerce_optional_str`, `_parse_task_kwargs_str`, `_is_helping_hands_task`, `_upsert_current_task`, `_flower_timeout_seconds`, `_task_state_priority`, `_iter_worker_task_entries`, `_is_running_in_docker`, and health/schedule endpoints have no dedicated unit tests — they're only exercised indirectly through integration-style endpoint tests.
3. **Doc reconciliation** — Obsidian Project Log needs current work entry.
4. **MCP `read_file` bug** — Exception handler ordering incorrect: `UnicodeError` (subclass of `ValueError`) was caught by the `ValueError` handler first, producing misleading error messages for binary files.

Note: All `app.py` internal helpers already have Google-style docstrings (verified during audit).

## Success Criteria

- [x] All `app.py` internal helpers verified to have docstrings (confirmed — no work needed)
- [x] MCP server has 17 new edge-case tests
- [x] Server app has 47 new internal-helper unit tests
- [x] MCP `read_file` exception handler ordering fixed
- [x] Obsidian Project Log W09 updated with current work entry
- [x] Weekly progress index updated with W09
- [x] AGENT.md updated with new recurring decisions
- [x] Project todos design notes updated
- [x] All lint checks pass (`ruff check`, `ruff format --check`)
- [x] All 488 tests pass (`uv run pytest -v`)
- [x] No factual inconsistencies between documentation surfaces

## Non-Goals

- Rewriting existing code behavior (beyond bug fix)
- Adding frontend component tests (separate PRD scope)
- Adding a docstring linter to CI

---

## TODO

### 1. Add MCP server edge-case tests
- [x] `_repo_root()` raises FileNotFoundError for missing directory
- [x] `_repo_root()` resolves valid directory
- [x] `_command_result_to_dict()` converts all fields correctly
- [x] `_command_result_to_dict()` success on zero exit code
- [x] `read_file()` raises IsADirectoryError for directories
- [x] `read_file()` raises UnicodeError for binary files
- [x] `build_feature()` rejects invalid skill names
- [x] `build_feature()` passes custom backend and all params
- [x] `run_bash_script()` with inline_script parameter
- [x] `run_python_code()` with non-zero exit code
- [x] `run_python_code()` with timeout
- [x] `web_search()` empty results
- [x] `web_browse()` truncated response
- [x] `web_browse()` redirect detection
- [x] `list_indexed_repos()` format with multiple repos
- [x] `main()` entry point stdio transport
- [x] `main()` entry point http transport

### 2. Add server app internal helper unit tests
- [x] `_parse_backend()` valid backends, normalization, invalid input, empty string
- [x] `_normalize_task_status()` normal, None, empty, whitespace, mixed case
- [x] `_extract_task_id()` from task_id/uuid/id keys, nested request, empty, whitespace, priority
- [x] `_extract_task_name()` from name/task keys, nested request, empty, whitespace
- [x] `_extract_task_kwargs()` from dict, JSON string, literal string, nested request, missing, unparseable
- [x] `_coerce_optional_str()` normal, trimmed, empty, whitespace, non-string types
- [x] `_parse_task_kwargs_str()` JSON, literal eval, empty, whitespace, invalid, non-dict JSON
- [x] `_is_helping_hands_task()` matching, non-matching, missing name
- [x] `_upsert_current_task()` insert, merge higher priority, keep higher existing, fill missing fields
- [x] `_flower_timeout_seconds()` default, custom, min clamp, max clamp, invalid
- [x] `_task_state_priority()` known states, unknown, case sensitivity
- [x] `_iter_worker_task_entries()` valid, non-dict payload, non-list tasks, non-dict entries, non-string keys
- [x] `_is_running_in_docker()` dockerenv file, env var true/yes, not in docker
- [x] `/health` endpoint returns ok
- [x] `/health/services` endpoint returns all fields
- [x] JSON `/build` endpoint enqueues task, validates empty repo/prompt, validates max_iterations bounds
- [x] `/tasks/{id}` endpoint returns pending status
- [x] `/config` endpoint in/out of docker

### 3. Fix MCP `read_file` exception handler ordering
- [x] Reorder `except` clauses: `UnicodeError` before `ValueError`

### 4. Reconcile documentation
- [x] Update Obsidian Project Log W09 with current work entry
- [x] Update Weekly progress index with W09
- [x] Update AGENT.md recurring decisions (exception ordering, test coverage)
- [x] Update Obsidian Project todos design notes
- [x] Verify cross-surface consistency

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created; audit identified 3 improvement areas |
| 2026-03-01 | Verified all app.py internal helpers already have docstrings — no work needed |
| 2026-03-01 | Added 17 MCP server edge-case tests to `tests/test_mcp_server.py` |
| 2026-03-01 | Fixed MCP `read_file` exception handler ordering — `UnicodeError` now caught before `ValueError` |
| 2026-03-01 | Created `tests/test_server_app_helpers.py` with 47 internal helper unit tests |
| 2026-03-01 | All 488 tests pass, lint/format checks clean |
| 2026-03-01 | Updated Obsidian Project Log W09, Weekly progress index, Project todos design notes |
| 2026-03-01 | Updated AGENT.md with exception ordering and test coverage recurring decisions |
| 2026-03-01 | PRD complete; moving to completed/ |
