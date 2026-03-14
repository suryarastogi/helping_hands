# Execution plan: Codex CLI and Gemini CLI hand implementation

**Date**: 2026-03-14
**Status**: Active

## Goal

Implement real subprocess execution for CodexCLIHand and GeminiCLIHand,
replacing scaffold placeholders. Add docs structure per template.

## Tasks

- [x] Implement `CodexCLIHand.run()` with subprocess execution
- [x] Implement `CodexCLIHand.stream()` with async subprocess
- [x] Implement `GeminiCLIHand.run()` with subprocess execution
- [x] Implement `GeminiCLIHand.stream()` with async subprocess
- [x] Add tests for `CodexCLIHand` subprocess (build_command, success, error, timeout, not found)
- [x] Add tests for `GeminiCLIHand` subprocess (build_command, success, error, timeout, not found)
- [x] Create `docs/references/` with LLM reference files
- [x] Create `docs/exec-plans/completed/` directory
- [x] Move prior plan to completed
- [x] Update AGENTS.md and ARCHITECTURE.md (scaffold → implemented)
- [x] Update TODO.md with completed items
- [x] Run full test suite and lint

## Design decisions

### CodexCLIHand subprocess
- Mirrors ClaudeCodeHand pattern for consistency.
- Command: configurable via `HELPING_HANDS_CODEX_CLI_CMD` (default: `codex`).
- Passes prompt via `--quiet` flag.
- Timeout: 300s default, configurable via `HELPING_HANDS_CODEX_TIMEOUT`.

### GeminiCLIHand subprocess
- Mirrors ClaudeCodeHand pattern for consistency.
- Command: configurable via `HELPING_HANDS_GEMINI_CLI_CMD` (default: `gemini`).
- Passes prompt via `--prompt` flag.
- Timeout: 300s default, configurable via `HELPING_HANDS_GEMINI_TIMEOUT`.

## Risks

- CLI tools may not be installed in test/CI environments — tests mock subprocess.
- Exact CLI flags (`--quiet`, `--prompt`) may need adjustment when real CLIs are tested.
