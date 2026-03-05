# Execution Plan: Docs and Testing v6

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Expand test coverage for CLI hand helpers, web tool internals, and registry payload validators; improve SECURITY.md and RELIABILITY.md documentation.

---

## Tasks

### Phase 1: Testing improvements

- [x] Add Goose CLI helper tests (20 tests): `_normalize_goose_provider`,
  `_infer_goose_provider_from_model`, `_normalize_ollama_host`
- [x] Add `_TwoPhaseCLIHand` utility tests (14 tests): `_is_truthy`,
  `_truncate_summary`, `_looks_like_edit_request`, `_float_env`
- [x] Add web tool internal tests (13 tests): `_require_http_url`,
  `_decode_bytes`, `_strip_html`, `_as_string_keyed_dict`
- [x] Add registry payload validator tests (19 tests): `_parse_str_list`,
  `_parse_positive_int`, `_parse_optional_str`
- [x] Add `_StreamJsonEmitter._summarize_tool` tests (9 tests): Read, Edit,
  Write, Bash truncation, Glob, Grep, unknown tool

### Phase 2: Documentation improvements

- [x] Update `docs/SECURITY.md` with iterative hand security boundaries
  (BasicLangGraphHand, BasicAtomicHand execution model, tool dispatch, network)
- [x] Update `docs/RELIABILITY.md` with iterative hand failure modes
  (provider API failures, context exhaustion, @@READ/@@FILE parse errors,
  @@TOOL dispatch, early completion)

### Phase 3: Validation

- [x] All tests pass: 589 passed, 2 skipped
- [x] Lint clean: `uv run ruff check .` all checks passed
- [x] Format clean: `uv run ruff format --check .` all formatted
- [x] Move plan to completed, update `docs/PLANS.md`

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest --ignore=tests/test_schedules.py -v` passes (589 passed, 2 skipped)
- `uv run ruff check .` passes
