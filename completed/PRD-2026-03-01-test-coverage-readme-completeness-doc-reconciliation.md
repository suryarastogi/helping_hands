# PRD: Test Coverage Hardening, README Completeness, and Doc Reconciliation

**Date:** 2026-03-01
**Scope:** Test coverage for undertested tool modules, README feature completeness, cross-surface doc reconciliation

## Goals

1. Close critical test coverage gaps in `lib/meta/tools/command.py` and `lib/meta/tools/web.py` private helpers
2. Add missing user-facing features to README.md (skills, MCP runtime, cron, verbose flag)
3. Reconcile all documentation surfaces (README, CLAUDE.md, AGENT.md, obsidian, docs/index.md) for consistency

## Success Criteria

- All private helper functions in `command.py` and `web.py` have dedicated unit tests
- README.md documents `--skills`, `--verbose/-v`, MCP commands, and cron scheduling
- No cross-surface inconsistencies in feature descriptions, test counts, or module counts
- All tests pass (`uv run pytest -v`)

---

## TODO

- [x] **T1: Add tests for `command.py` private helpers** — `_normalize_args`, `_resolve_cwd`, `_resolve_python_command`, `_run_command` (timeout path, zero timeout, nonzero exit)
- [x] **T2: Add tests for `web.py` private helpers** — `_require_http_url`, `_decode_bytes`, `_strip_html`, `_as_string_keyed_dict`, `_extract_related_topics`
- [x] **T3: Add `--skills` and `--verbose/-v` to README CLI flags table** — currently missing from the CLI flags section
- [x] **T4: Add MCP runtime commands to README** — `uv run helping-hands-mcp` (stdio) and `--http` mode
- [x] **T5: Add cron scheduling section to README** — currently only in CLAUDE.md and obsidian
- [x] **T6: Add frontend dev commands to README Development section** — currently only in CLAUDE.md
- [x] **T7: Update obsidian project log** — add W10 entry for this session's work
- [x] **T8: Run full test suite** — verify all tests pass including new ones

---

## Activity Log

- **2026-03-01 T06:35 UTC** — PRD created after comprehensive audit of source, tests, docs, and obsidian vault. Identified 8 actionable items across test coverage, README completeness, and doc reconciliation.
- **2026-03-01 T06:40 UTC** — T1 complete: added 24 tests for `command.py` private helpers (`_normalize_args` 5 tests, `_resolve_cwd` 5 tests, `_resolve_python_command` 4 tests, `_run_command` 7 tests, `CommandResult.success` 3 tests). Coverage: 96%.
- **2026-03-01 T06:42 UTC** — T2 complete: added 23 tests for `web.py` private helpers (`_require_http_url` 6 tests, `_decode_bytes` 4 tests, `_strip_html` 5 tests, `_as_string_keyed_dict` 4 tests, `_extract_related_topics` 4 tests) plus 8 additional validation tests for public API edge cases. Coverage: 98%.
- **2026-03-01 T06:45 UTC** — T3-T6 complete: added `--skills`, `--verbose/-v`, `--enable-execution`, `--enable-web` to README CLI flags. Added MCP server section with runtime commands. Added cron scheduling section with API examples. Added frontend dev commands to Development section.
- **2026-03-01 T06:47 UTC** — T7 complete: added W10 project log entry summarizing this session's work.
- **2026-03-01 T06:48 UTC** — T8 complete: 569 tests passed, 4 skipped. Lint clean. All TODO items executed successfully. PRD moved to `completed/`.
