# Claude Code CLI Feature Flags

Design document for the opt-in feature-flag injection layer in
`ClaudeCodeHand` that surfaces native Claude Code CLI capabilities through
environment variables, without changing the default backend behavior.

## Overview

The Claude Code CLI exposes many flags useful for automation that
`helping_hands` previously didn't pass through:

- `--max-turns` — bound the agentic loop length per invocation
- `--append-system-prompt` — inject project-specific guidance
- `--allowedTools` / `--disallowedTools` — narrow the tool surface
- `--continue --session-id` — reuse a captured session across phases

Each flag is opt-in via a `HELPING_HANDS_CLAUDE_*` environment variable.
When unset, the backend behaves identically to before. The injection layer
is purely additive — it composes with the existing `--output-format
stream-json` output, `--dangerously-skip-permissions` default, and the
two-phase init/task lifecycle.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `HELPING_HANDS_CLAUDE_MAX_TURNS` | Cap on agentic turns. `0` = unlimited. | `0` |
| `HELPING_HANDS_CLAUDE_SYSTEM_PROMPT` | Explicit system prompt text. Overrides auto-read. | unset |
| `HELPING_HANDS_CLAUDE_ALLOWED_TOOLS` | Comma-separated allow-list (e.g. `Read,Edit,Bash`). | unset |
| `HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS` | Comma-separated deny-list (e.g. `WebFetch,WebSearch`). | unset |
| `HELPING_HANDS_CLAUDE_SESSION_CONTINUE` | When `1`/`true`/`yes`/`on`, reuse session ID across invocations. | `0` |

## Architecture

The injection happens in `ClaudeCodeHand._build_cli_cmd()`, called from
`_invoke_claude()` instead of `_render_command()` directly. The pipeline
preserves the existing `_render_command → _inject_output_format` flow and
layers feature flags on top:

```
prompt
  │
  ▼
_render_command(prompt)            # base: model, prompt, defaults
  │
  ▼
_inject_output_format(stream-json) # always: enables _StreamJsonEmitter
  │
  ▼
_inject_max_turns(n)               # if HH_CLAUDE_MAX_TURNS > 0
  │
  ▼
_inject_system_prompt(text)        # if env var set OR AGENT.md/CLAUDE.md exists
  │
  ▼
_inject_tool_filters(allow, deny)  # if HH_CLAUDE_*_TOOLS set
  │
  ▼
_inject_continue(session_id)       # if HH_CLAUDE_SESSION_CONTINUE=1 AND
                                   #    a session ID was captured earlier
  │
  ▼
final command list
```

Each `_inject_*` helper is idempotent: it checks `has_cli_flag()` and skips
the injection if a user-provided override is already in the rendered
command (so explicit `HELPING_HANDS_CLAUDE_CLI_CMD` overrides win).

### Insertion point

All flags insert immediately **before** the `-p` flag, which is the
conventional position for CLI options that accept arguments. This keeps
them outside the prompt argument and visually grouped with other
non-interactive control flags. If `-p` is absent (custom override), the
flags append to the end of the command.

### `--append-system-prompt` resolution order

The system prompt content resolves in this priority:

1. `HELPING_HANDS_CLAUDE_SYSTEM_PROMPT` (env var, explicit override)
2. `AGENT.md` at the repo root (read at injection time)
3. `CLAUDE.md` at the repo root (fallback)

If none are present, no flag is injected. Content is truncated to 16,000
characters with a `...[truncated]` marker to stay under Claude Code's CLI
argument-size limit. The auto-read makes the backend honor whatever
project-specific guidance the repo already publishes for human and AI
contributors, without users needing to set anything.

### Session continuation

The `_StreamJsonEmitter` captures `session_id`, `total_cost_usd`,
`duration_ms`, and token usage from `result` events. After each
invocation, `_invoke_claude` stores `parser.session_id` on the hand
instance as `_last_session_id` and accumulates `total_cost_usd` into
`_cumulative_cost_usd`. Both are exposed via the `cost_metadata` property
for callers that want to inspect the running totals.

When `HELPING_HANDS_CLAUDE_SESSION_CONTINUE=1` and a session ID has been
captured, the next `_invoke_claude` call adds `--continue --session-id <id>`
*alongside* `-p`. Current Claude Code (>= 2.x) accepts these flags
together; older docs sometimes show `--continue` replacing `-p`, but that
is not how the present CLI works.

The default is **off** because the two phases of `_TwoPhaseCLIHand`
intentionally start with fresh context (init explores the repo, task
applies changes). Operators who want explicit context carry-over opt in
deliberately.

## Composition with existing behavior

- The `--output-format stream-json` flag is always injected first; the
  `_StreamJsonEmitter` parses every event regardless of which other
  feature flags are present.
- `--dangerously-skip-permissions` is still added by `_apply_backend_defaults`
  in `_render_command`, before this layer runs.
- Container mode (`HELPING_HANDS_CLAUDE_CONTAINER=1`) wraps the *final*
  command produced by `_build_cli_cmd`, so all feature flags propagate
  inside the container.
- `HELPING_HANDS_CLAUDE_CLI_CMD` overrides take precedence — if the
  override already specifies, e.g., `--max-turns`, the corresponding
  injection is skipped.

## CLI compatibility note

The flags chosen here all work in Claude Code CLI 2.1.x. Several flags
that appeared in early prototypes — `--thinking-budget`, `--budget-tokens`,
`--cwd`, `--no-user-input`, `--no-user-profile` — have been removed from
the CLI and are not supported. If those return in a future Claude Code
version they can be added back through the same injection pattern.

## Testing

`tests/test_cli_hand_claude_new_features.py` covers each helper in
isolation (env var parsing, idempotent injection, ordering) plus a
`TestBuildCliCmd` integration class that exercises `_build_cli_cmd` with
combinations of features enabled.

The session-continuation test seeds `_last_session_id` directly on the
hand and checks that `_build_cli_cmd` emits `--continue --session-id`
without leaving the prior context to test scaffolding.
