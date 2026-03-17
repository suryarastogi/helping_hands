# v268 — DRY Label Prefix, Error Exit, and Temp Clone Dir

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

Three recurring patterns remained un-DRYed after v267:

1. `_StreamJsonEmitter` in `claude.py` used `f"[{self._label}] ..."` 4 times inline,
   and `DockerSandboxClaudeCodeHand` used `f"[{self._CLI_LABEL}] ..."` 5 times,
   plus `ClaudeCodeHand._invoke_claude` used it once — all bypassing the
   `_label_msg()` helper added in v267.
2. `cli/main.py` had 5 `print(f"Error: ...", file=sys.stderr); sys.exit(1)` blocks.
3. `cli/main.py` had 2 identical `mkdtemp() + atexit.register() + dest / "repo"`
   blocks in `_resolve_repo_path` and `_clone_reference_repos`.

## Tasks

- [x] Add `_label_msg()` to `_StreamJsonEmitter`, replace 4 inline patterns in `claude.py`
- [x] Replace 1 inline `f"[{self._CLI_LABEL}]"` in `ClaudeCodeHand._invoke_claude`
- [x] Replace 5 inline `f"[{self._CLI_LABEL}]"` patterns in `docker_sandbox_claude.py`
- [x] Extract `_error_exit()` helper in `cli/main.py`, replace 5 inline error+exit blocks
- [x] Remove `"Error: "` prefix from `_MODEL_NOT_AVAILABLE_MSG` (was double-prefixed)
- [x] Extract `_make_temp_clone_dir()` helper in `cli/main.py`, replace 2 inline blocks
- [x] Add 4 tests for `_error_exit()` in `test_cli.py`
- [x] Add 4 tests for `_make_temp_clone_dir()` in `test_cli.py`
- [x] Add 5 tests for `_StreamJsonEmitter._label_msg()` in `test_claude_stream_emitter.py`
- [x] Run full test suite — 6237 passed, 272 skipped
- [x] Ruff lint + format clean

## Completion criteria

- [x] Zero remaining inline `f"[{self._label}]"` or `f"[{self._CLI_LABEL}]"` in `claude.py` and `docker_sandbox_claude.py`
- [x] Zero remaining `print(..., file=sys.stderr); sys.exit(1)` outside `_error_exit` in `cli/main.py`
- [x] Zero remaining `mkdtemp(...); atexit.register(...)` outside `_make_temp_clone_dir` in `cli/main.py`
- [x] All tests pass, ruff clean

## Changes

- `src/helping_hands/lib/hands/v1/hand/cli/claude.py` — added `_label_msg()` to `_StreamJsonEmitter`, replaced 5 inline patterns
- `src/helping_hands/lib/hands/v1/hand/cli/docker_sandbox_claude.py` — replaced 5 inline label patterns with `self._label_msg()`
- `src/helping_hands/cli/main.py` — added `_error_exit()`, `_make_temp_clone_dir()`, removed `"Error: "` from `_MODEL_NOT_AVAILABLE_MSG`, replaced all inline patterns
- `tests/test_cli.py` — 8 new tests in `TestErrorExit` and `TestMakeTempCloneDir` classes
- `tests/test_claude_stream_emitter.py` — 5 new tests in `TestStreamJsonEmitterLabelMsg` class

## Test results

- 6237 passed, 272 skipped (17 net new tests)
