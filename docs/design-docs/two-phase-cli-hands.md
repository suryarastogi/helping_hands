# Two-Phase CLI Hands

Design document for the two-phase subprocess architecture used by CLI-backed
hands (Claude Code, Codex, Goose, Gemini, OpenCode).

## Overview

CLI hands delegate work to external AI CLI tools running as subprocesses.
Each execution follows a **two-phase pattern**:

1. **Phase 1 — Initialization**: Orient the CLI tool to the repo structure,
   conventions, and codebase layout. The tool reads files and builds context
   but is not expected to make changes.

2. **Phase 2 — Task execution**: Deliver the user's actual task prompt along
   with a summary of what the init phase learned. The CLI tool applies changes
   to the working directory.

This separation gives external tools repo context before acting, improving
the quality of generated changes.

## Architecture

```
User prompt
    │
    ▼
_TwoPhaseCLIHand._run_two_phase()
    │
    ├─ Phase 1: _invoke_backend(init_prompt)
    │     └─ _invoke_cli(prompt) → _invoke_cli_with_cmd(cmd)
    │           └─ asyncio.create_subprocess_exec(...)
    │                 └─ stdout polling loop with heartbeat + idle timeout
    │
    ├─ Phase 2: _invoke_backend(task_prompt + init_summary)
    │     └─ same subprocess flow
    │
    ├─ Optional: retry enforcement pass (ClaudeCodeHand only)
    │     └─ if edit prompt produced no file changes, re-invoke with
    │        enforcement prompt
    │
    └─ _finalize_repo_pr()
          └─ commit / push / PR creation (inherited from Hand base)
```

## Backend lifecycle

Each CLI hand subclass provides:

| Hook | Purpose |
|---|---|
| `_BACKEND_NAME` | Identifier for metadata/logging |
| `_DEFAULT_CLI_CMD` | Default command template |
| `_COMMAND_ENV_VAR` | Env var to override the CLI command |
| `_apply_backend_defaults(cmd)` | Inject backend-specific flags |
| `_build_subprocess_env()` | Prepare environment (auth, tokens) |
| `_build_failure_message(rc, output)` | Human-readable error from failure |
| `_command_not_found_message(cmd)` | Install hint when binary is missing |
| `_invoke_backend(prompt, emit=)` | Entry point for subprocess execution |

## Command rendering

Commands are rendered via `_render_command(prompt)`:

1. Parse `_DEFAULT_CLI_CMD` or `$COMMAND_ENV_VAR` into tokens
2. Normalize shorthand (e.g. `codex` → `codex exec`, `goose` → `goose run --with-builtin developer --text`)
3. Expand placeholders: `{model}`, `{repo}`, `{prompt}`, `{repo_tree}`
4. Inject `--model` flag if model is set and not already present
5. Apply backend defaults (sandbox mode, approval mode, permissions)
6. Optionally wrap in `docker run` if container mode is enabled
7. Append prompt as the final positional argument

## Retry and fallback logic

### Command not found fallback

If the primary command is not found (`FileNotFoundError` from subprocess):

- `_fallback_command_when_not_found(cmd)` is called
- Claude Code falls back to `npx -y @anthropic-ai/claude-code`
- Other backends return `None` (hard failure)

### Failure retry

After a non-zero exit from the subprocess:

- `_retry_command_after_failure(cmd, output=, return_code=)` is called
- **Claude Code**: strips `--dangerously-skip-permissions` if root permission
  error is detected
- **Gemini**: strips `--model` flag if model-not-found error is detected
- Returns `None` to skip retry, or a modified command to retry with

### No-change enforcement (Claude Code)

When `_RETRY_ON_NO_CHANGES = True` and the task prompt looks like an edit
request but no files were modified:

1. A follow-up enforcement prompt is sent asking the CLI to apply changes
2. If the enforcement pass still produces no changes, output is checked for
   permission-prompt markers
3. A `RuntimeError` is raised if permission approval was the blocker

## Subprocess execution details

`_invoke_cli_with_cmd(cmd, emit=)`:

- Spawns via `asyncio.create_subprocess_exec` with `stdin=DEVNULL`
- Polls stdout in a read loop (`_IO_POLL_SECONDS` intervals)
- Emits heartbeat lines every `_HEARTBEAT_SECONDS` showing elapsed time
- Terminates the process after `_IDLE_TIMEOUT_SECONDS` of no output
- Raises `RuntimeError` on timeout; returns captured stdout on success

## Authentication patterns

| Backend | Auth env vars | Validation |
|---|---|---|
| Claude Code | `ANTHROPIC_API_KEY` | Optional (CLI has its own auth) |
| Codex | `OPENAI_API_KEY` | Optional |
| Goose | `GH_TOKEN`/`GITHUB_TOKEN` + `GOOSE_PROVIDER` | Token required; provider inferred from model |
| Gemini | `GEMINI_API_KEY` | Required (RuntimeError if missing) |
| OpenCode | Provider-specific key | Optional |

All backends support `--use-native-cli-auth` to strip API keys from the
subprocess environment, letting the external CLI use its own credential store.

## Container isolation

Codex and Claude Code support optional Docker wrapping:

- Enabled via `$HELPING_HANDS_{BACKEND}_CONTAINER=1`
- Image set via `$HELPING_HANDS_{BACKEND}_CONTAINER_IMAGE`
- Wraps the command in `docker run --rm -i` with:
  - Repo bind-mounted at `/workspace`
  - API keys passed as `-e` flags
  - Working directory set to `/workspace`
