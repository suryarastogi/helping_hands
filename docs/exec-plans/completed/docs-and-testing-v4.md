# Execution Plan: Docs and Testing v4

**Status:** Completed
**Created:** 2026-03-04
**Completed:** 2026-03-04
**Goal:** Expand AI provider and CLI hand test coverage, add two-phase CLI hands design doc, enhance SECURITY.md.

---

## Tasks

### Phase 1: Testing improvements

- [x] Add AI provider tests: lazy-init caching, `acomplete` async wrapper,
  `normalize_messages` edge cases (empty sequence, missing keys), model override,
  Anthropic max_tokens override, Google empty-content filtering, class attributes
- [x] Add `_StreamJsonEmitter` unit tests (12 tests): assistant text events,
  tool_use summaries (Read/Edit/Write/Bash/Glob/Grep/unknown), user tool_result
  events, result events with cost/duration, non-JSON passthrough, flush buffered,
  result_text fallback to text_parts, Bash command truncation
- [x] Add `ClaudeCodeHand._inject_output_format` tests (3 tests): insertion
  before `-p`, no-op when already present, append when no `-p` flag
- [x] Add `GooseCLIHand` static helper tests (13 tests): `_normalize_goose_provider`
  (gemini→google, passthrough, empty), `_infer_goose_provider_from_model` (claude,
  gemini, llama, default→openai), `_normalize_ollama_host` (add scheme, preserve
  https, strip path, empty, invalid scheme), `_has_goose_builtin_flag` (present,
  missing)
- [x] Add `GeminiCLIHand` static helper tests (7 tests): `_looks_like_model_not_found`
  (true/false), `_extract_unavailable_model` (match/no-match), `_strip_model_args`
  (flag-value pair, equals form, no model returns None)

### Phase 2: Documentation improvements

- [x] Add design doc `docs/design-docs/two-phase-cli-hands.md` covering
  architecture diagram, backend lifecycle hooks, command rendering pipeline,
  retry/fallback logic, subprocess execution details, auth patterns, container isolation
- [x] Enhance `docs/SECURITY.md` with execution sandboxing: Codex sandbox modes,
  Claude --dangerously-skip-permissions safety checks, container isolation for CLI
  hands, Gemini approval mode
- [x] Update `docs/design-docs/index.md` with new design doc

### Phase 3: Validation

- [x] All tests pass: 470 passed, 2 skipped
- [x] Lint clean: `uv run ruff check .` all checks passed
- [x] Format clean: `uv run ruff format --check .` all formatted
- [x] Move plan to completed, update `docs/PLANS.md`

---

## Completion criteria

- All Phase 1–3 tasks checked off
- `uv run pytest --ignore=tests/test_schedules.py -v` passes (470 passed, 2 skipped)
- `uv run ruff check .` passes
