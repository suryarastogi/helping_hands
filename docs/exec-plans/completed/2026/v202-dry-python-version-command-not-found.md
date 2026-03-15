# v202 — DRY Python version default + command-not-found messages

**Status:** Completed
**Created:** 2026-03-15

## Problem

1. The default Python version `"3.13"` is hardcoded in 2 MCP server function
   signatures (`run_python_code`, `run_python_script`) instead of importing
   `_DEFAULT_PYTHON_VERSION` from `command.py` where the single source of
   truth already exists.

2. `_command_not_found_message()` is overridden in 5 CLI hand subclasses
   (claude, codex, gemini, goose, opencode) when the base class already has
   `_CLI_DISPLAY_NAME`, `_COMMAND_ENV_VAR`, and `_CLI_LABEL` class attributes
   that make most overrides redundant. 4 overrides add
   `_DOCKER_REBUILD_HINT_TEMPLATE.format(cli_label)` which belongs in the
   base. 1 override (claude) is identical to the base implementation.

## Tasks

- [x] Import `_DEFAULT_PYTHON_VERSION` in `mcp_server.py`, replace 2× hardcoded `"3.13"`
- [x] Enhance base `_command_not_found_message` to include Docker rebuild hint via `_CLI_LABEL`
- [x] Remove redundant `_command_not_found_message` overrides from claude/codex/gemini/goose/opencode
- [x] Add tests for `_DEFAULT_PYTHON_VERSION` import identity in mcp_server
- [x] Add tests for base `_command_not_found_message` Docker hint inclusion
- [x] Add tests verifying subclasses inherit base message (no override)
- [x] Update docs (Week-12, PLANS.md)

## Completion criteria

- `mcp_server.py` uses `_DEFAULT_PYTHON_VERSION` from `command.py`
- Base `_command_not_found_message` generates messages with Docker rebuild hint
- No redundant overrides in 5 CLI hand subclasses
- Tests pass, ruff clean
