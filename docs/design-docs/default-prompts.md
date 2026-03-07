# Default Prompts

How helping_hands defines and shares default prompts across entry points.

## Context

The project needs a canonical smoke-test prompt that exercises all core agent
capabilities (file reading, file writing, code execution, web tools) across
both CLI and server entry points. Rather than duplicating prompt text, a shared
module provides a single source of truth.

## Decision

Default prompts live in `lib/default_prompts.py` as module-level string
constants. Both `cli/main.py` and `server/app.py` import from this module
rather than defining their own defaults.

### Prompt structure

`DEFAULT_SMOKE_TEST_PROMPT` is a multi-line string that guides an AI agent
through a structured smoke test:

1. **Read** -- `@@READ` to inspect `README.md` (tests file reading)
2. **Write** -- `@@FILE` to apply updates (tests file editing)
3. **Code execution** -- `@@TOOL python.run_code` and `@@TOOL python.run_script`
   (conditional on `enable_execution`)
4. **Shell execution** -- `@@TOOL bash.run_script` (conditional on
   `enable_execution`)
5. **Web tools** -- `@@TOOL web.search` and `@@TOOL web.browse` (conditional on
   `enable_web`)

Each step is numbered so agents process them sequentially. Conditional steps
use "If ... tools are enabled" phrasing so agents skip them when the capability
is not available.

### Directive flow

```
lib/default_prompts.py   (canonical constants)
        |
        +---> cli/main.py        (--prompt default value)
        +---> server/app.py      (form textarea default)
```

The CLI uses the constant as the default when `--prompt` is omitted. The server
pre-fills the submission form textarea with the same constant so the smoke-test
prompt is one click away.

## Alternatives considered

1. **Inline defaults per entry point** -- Rejected because duplicated prompt
   text drifts out of sync when capabilities are added.
2. **YAML/JSON prompt templates** -- Rejected as over-engineering; the prompt
   is a single constant that rarely changes.
3. **Per-backend prompt variants** -- Not needed; the conditional phrasing
   ("If tools are enabled") handles capability differences at runtime.

## Consequences

- Adding a new tool category means updating one constant, not two+ entry points.
- The smoke-test prompt doubles as integration-test documentation: reading it
  shows which capabilities the project supports.
- Tests in `test_default_prompts.py` verify prompt content assertions
  (directive presence, guard phrases, tool references) against the constant
  directly.
