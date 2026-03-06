# Execution Plan: Docs and Testing v46

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Goal:** Cover remaining branch/line gaps in codex.py, opencode.py, cli/base.py, iterative.py, and skills/__init__.py delegation and edge case paths.

---

## Tasks

### Phase 1: CLI hand delegation coverage

- [x] codex.py line 95: `_build_failure_message` delegation to `_build_codex_failure_message`
- [x] codex.py line 114: `_invoke_codex` delegation to `_invoke_cli`
- [x] codex.py `_invoke_backend` delegation to `_invoke_codex`
- [x] opencode.py line 68: `_invoke_opencode` delegation
- [x] opencode.py line 76: `_invoke_backend` delegation
- [x] Note: codex.py line 62 is dead code (`_auto_sandbox_mode()` always returns truthy)

### Phase 2: CLI base.py coverage

- [x] cli/base.py line 482: `_invoke_cli` delegation to `_invoke_cli_with_cmd`
- [x] cli/base.py `stream()` producer error re-raise
- [x] Note: line 985 (noop emit pass) and 1047-1049 (producer cancel) are hard-to-reach defensive paths

### Phase 3: iterative.py Atomic stream() exception path

- [x] iterative.py lines 835-836: `except Exception: raise` in Atomic `stream()` (non-AssertionError from `run_async`)
- [x] Note: lines 830 and 858 are dead code (`stream_text` is always `""` at those points)

### Phase 4: skills catalog edge case

- [x] skills/__init__.py line 36: `_discover_catalog` returns empty when `_CATALOG_DIR` is not a directory

### Phase 5: Documentation

- [x] Update QUALITY_SCORE.md with new test entries
- [x] Update docs/PLANS.md

### Phase 6: Validation

- [x] All tests pass (1440 passed)
- [x] Lint and format clean
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-6 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
