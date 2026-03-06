# Execution Plan: Docs and Testing v49

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Goal:** Close remaining coverage gaps in MCP server entry point, CLI base IO loop edge cases, and CI-fix noop-emit path. Update product docs.

---

## Tasks

### Phase 1: MCP server main() coverage (97% -> 98%)

- [x] Test `main()` with `--http` in sys.argv (streamable-http transport)
- [x] Test `main()` without `--http` (stdio transport)

### Phase 2: CLI base IO loop edge cases (98% -> 99%+)

- [x] Test `_invoke_cli_with_cmd` interrupt during IO loop (lines 538-540)
- [x] Test `_invoke_cli_with_cmd` process.returncode set during TimeoutError (line 549)
- [x] Test `run()` CI-fix path with _noop_emit (line 985)

### Phase 3: Documentation updates

- [x] Update PRODUCT_SENSE.md with scheduling status and MCP tool coverage
- [x] Update QUALITY_SCORE.md with new coverage entries
- [x] Update docs/PLANS.md with v49 entry

### Phase 4: Validation

- [x] All tests pass (1461 passed, 6 skipped)
- [x] Lint and format clean
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-4 tasks checked off
- `uv run pytest -v` passes (1461 tests)
- `uv run ruff check . && uv run ruff format --check .` passes
