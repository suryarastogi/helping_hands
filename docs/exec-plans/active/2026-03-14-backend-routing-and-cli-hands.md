# Execution plan: Backend routing and CLI hand implementation

**Date**: 2026-03-14
**Status**: Active
**Author**: E2EHand (CI integration run)

## Goal

Implement the two most actionable items from TODO.md:
1. Backend selection/routing via config and CLI flag
2. ClaudeCodeHand subprocess execution (replacing scaffold)

## Tasks

- [x] Add `backend` field to `Config` dataclass
- [x] Add `HELPING_HANDS_BACKEND` env var support
- [x] Add `--backend` CLI flag
- [x] Add `create_hand()` factory function for backend routing
- [x] Implement `ClaudeCodeHand.run()` with subprocess execution
- [x] Implement `ClaudeCodeHand.stream()` with subprocess execution
- [x] Add tests for backend selection in config
- [x] Add tests for `create_hand()` factory
- [x] Add tests for `ClaudeCodeHand` subprocess execution
- [x] Update documentation (AGENTS.md, ARCHITECTURE.md, TODO.md)
- [x] Create docs directory structure per template
- [x] Run full test suite and lint

## Design decisions

### Backend routing
- Factory function `create_hand(config, repo_index)` returns the correct Hand
  subclass based on `config.backend`.
- Default backend: `"langgraph"` (matches existing behaviour).
- Invalid backend raises `ValueError` with available options.

### ClaudeCodeHand subprocess
- Uses `subprocess.run()` for `run()`, `subprocess.Popen` for `stream()`.
- Command: configurable via `HELPING_HANDS_CLAUDE_CLI_CMD` (default: `claude`).
- Timeout: 300s default.
- Passes prompt via `--print` / `-p` flag for non-interactive use.
- Working directory set to repo root.

## Risks

- CLI hand CLIs may not be installed in test environments — tests mock subprocess.
- Streaming implementation depends on CLI supporting incremental output.
