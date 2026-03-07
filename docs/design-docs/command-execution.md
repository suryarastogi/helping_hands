# Command Execution and Tool Registry

How helping_hands provides path-confined command execution and a composable
tool registry for iterative and CLI-backed hands.

## Context

Iterative hands need to run Python code, Python scripts, Bash scripts, web
searches, and URL browsing as part of their agent loops. CLI-backed hands
delegate execution to external CLIs but still need to communicate which tool
categories are enabled. Two modules handle this:

- `lib/meta/tools/command.py` -- path-confined Python/Bash execution
- `lib/meta/tools/registry.py` -- declarative tool registry, dispatch, and CLI guidance

Both are surfaced through `lib/meta/tools/__init__.py` and share the
filesystem security layer from `lib/meta/tools/filesystem.py`.

## CommandResult dataclass

All command execution functions return a frozen `CommandResult`:

```python
@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
```

The `success` property combines `exit_code == 0` and `not timed_out` for
uniform result checking.

## Path-confined execution

Every execution function resolves paths through `resolve_repo_target()`,
which prevents path traversal outside the repository root. Working directory
(`cwd`) is resolved relative to the repo root and validated as an existing
directory.

Key functions:
- `_resolve_cwd(repo_root, cwd)` -- validates and resolves working directory
- `_normalize_args(args)` -- validates argument lists contain only strings
- `_resolve_python_command(python_version)` -- finds `uv run --python` or
  bare `pythonX.Y` on PATH

## Python and Bash runners

Three public runners provide the execution surface:

| Runner | Input | Behavior |
|---|---|---|
| `run_python_code` | Inline code string | Writes to `-c` flag via resolved Python |
| `run_python_script` | Repo-relative path | Validates file exists and is not a directory |
| `run_bash_script` | Path or inline script | Repo-relative file, or temp file for inline |

All runners enforce:
- Non-empty input validation
- Timeout enforcement (default 60s, exit code 124 on timeout)
- Captured stdout/stderr (no terminal passthrough)
- Temp file cleanup for inline bash scripts (via `finally` block)

Python version resolution prefers `uv run --python` over bare `pythonX.Y`,
falling back with a clear error when neither is available.

## Tool registry

The registry (`registry.py`) wraps the raw execution functions into a
declarative, composable system:

### Data model

```
ToolCategory (frozen dataclass)
  name: str           -- category key ("execution", "web")
  title: str          -- human description
  tools: tuple[ToolSpec, ...]

ToolSpec (frozen dataclass)
  name: str           -- dotted tool name ("python.run_code")
  payload_example: dict  -- JSON-serializable example
  runner: callable    -- (root, payload) -> result
```

### Category selection flow

1. User passes `--tools execution,web` or legacy `--enable-execution` flags
2. `normalize_tool_selection()` deduplicates and normalizes names
3. `merge_with_legacy_tool_flags()` folds old boolean flags into the selection
4. `validate_tool_category_names()` rejects unknown categories
5. `resolve_tool_categories()` returns concrete `ToolCategory` objects

### Dispatch

For iterative hands, `build_tool_runner_map()` builds a
`tool_name -> callable` mapping. When the model emits `@@TOOL: python.run_code`,
the iterative loop looks up the runner and calls it with the parsed JSON
payload.

### CLI guidance translation

CLI-backed hands cannot use `@@TOOL` dispatch -- they have their own native
tool systems. Instead, `format_tool_instructions_for_cli()` produces
natural-language guidance:

```
Tool category enabled: execution -- Execution tools for Python/Bash runtime actions.
  - python.run_code: Run inline Python code using your shell/Bash tool. ...
```

This tells the external CLI (Codex, Claude Code, Goose, Gemini) to use its
own shell/Bash capabilities for execution tasks.

### Prompt generation

`format_tool_instructions()` generates `@@TOOL:` block prompts for iterative
hands, with JSON payload examples so the model knows the exact format to emit.

## Payload validation

Runner wrappers in the registry validate payloads before delegating to the
command module:

- `_parse_str_list` -- validates string arrays
- `_parse_positive_int` -- validates positive integers (rejects booleans)
- `_parse_optional_str` -- normalizes optional string fields (strips whitespace)

This keeps validation at the tool boundary, separate from the core execution
logic.

## Source references

- `src/helping_hands/lib/meta/tools/command.py` -- execution primitives
- `src/helping_hands/lib/meta/tools/registry.py` -- tool registry and dispatch
- `src/helping_hands/lib/meta/tools/filesystem.py` -- path confinement
- `tests/test_meta_tools_command.py` -- command execution tests
- `tests/test_meta_tools_registry.py` -- registry validation tests
- `tests/test_registry_runners.py` -- runner wrapper tests
- `tests/test_registry_validators.py` -- payload validator tests
