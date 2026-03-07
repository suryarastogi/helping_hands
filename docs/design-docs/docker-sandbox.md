# Docker Sandbox

How `DockerSandboxClaudeCodeHand` uses Docker Desktop microVM sandboxes to
isolate Claude Code execution.

## Context

CLI hands run AI tool CLIs as subprocesses on the host.  While this is
convenient, it grants the AI tool full access to the host filesystem and
network.  For higher-isolation scenarios, `DockerSandboxClaudeCodeHand`
wraps Claude Code execution inside a Docker Desktop microVM sandbox
(`docker sandbox create` / `docker sandbox exec`).

The sandbox backend is selected via `--backend docker-sandbox-claude`.

## Inheritance chain

`DockerSandboxClaudeCodeHand` extends `ClaudeCodeHand`, which extends
`_TwoPhaseCLIHand`, which extends the base `Hand`.  This means the sandbox
hand inherits all of Claude Code's two-phase lifecycle (init + task),
streaming JSON parsing (`_StreamJsonEmitter`), and PR finalization logic
while overriding only the isolation-specific methods.

Key overrides:

| Method | Purpose |
|---|---|
| `_invoke_claude` | Wraps the raw `claude -p` command with `docker sandbox exec` |
| `_run_two_phase` | Creates sandbox before execution, removes it after |
| `_execution_mode` | Returns `"docker-sandbox"` (controls logging labels) |
| `_build_failure_message` | Adds sandbox-specific auth and context hints |
| `_command_not_found_message` | Points to sandbox template installation |
| `_fallback_command_when_not_found` | Returns `None` (no npx fallback in sandbox) |

## Sandbox lifecycle

### Creation

`_ensure_sandbox()` runs `docker sandbox create --name <name> claude <workspace>`:

1. **Prerequisite checks** -- verifies `docker` is on PATH and `docker sandbox version` succeeds (Docker Desktop 4.49+ with sandbox plugin).
2. **Name resolution** -- `_resolve_sandbox_name()` uses `HELPING_HANDS_DOCKER_SANDBOX_NAME` if set, otherwise generates `hh-<repo>-<uuid8>`.  The name is cached for the lifetime of the hand instance.
3. **Template support** -- if `HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE` is set, passes `--template <image>` to use a custom base image.
4. **Workspace sync** -- the repo root directory is passed as the workspace argument, automatically synced at the same absolute path inside the sandbox.
5. **Output streaming** -- creation output (template pulls, microVM setup) is streamed to the emit callback in real time.

### Command wrapping

`_wrap_sandbox_exec()` transforms any command into a sandboxed equivalent:

```
[docker, sandbox, exec, --workdir, <workspace>, --env, KEY=VAL, ..., <name>, <original-cmd...>]
```

Only environment variables from `_effective_container_env_names()` that have
non-empty values are forwarded.  This prevents leaking unrelated host
environment into the sandbox.

### Cleanup

`_remove_sandbox()` runs `docker sandbox stop` followed by `docker sandbox rm`.
Cleanup is controlled by `HELPING_HANDS_DOCKER_SANDBOX_CLEANUP` (default `1`).
Set to `0` to keep the sandbox for post-run inspection.  Cleanup runs in the
`finally` block of `_run_two_phase`, so it executes even on task failure.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `HELPING_HANDS_DOCKER_SANDBOX_NAME` | auto-generated | Override sandbox name |
| `HELPING_HANDS_DOCKER_SANDBOX_CLEANUP` | `1` | Auto-remove sandbox after run |
| `HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE` | (none) | Custom base image template |

## Failure handling

The sandbox introduces unique failure modes beyond standard CLI hand errors:

- **Auth failures** -- the sandbox cannot access the host macOS Keychain, so
  OAuth login tokens are unavailable.  `_build_failure_message` detects
  "not logged in" or "authentication_failed" in output and suggests setting
  `ANTHROPIC_API_KEY` explicitly.
- **Docker not found** -- `_ensure_sandbox` raises `RuntimeError` if `docker`
  is not on PATH.
- **Plugin unavailable** -- `_docker_sandbox_available()` checks for the
  sandbox plugin; raises `RuntimeError` with upgrade instructions if missing.
- **Creation failure** -- non-zero exit from `docker sandbox create` raises
  `RuntimeError` with the full output for debugging.
- **Command not found** -- if the CLI is missing inside the sandbox,
  `_command_not_found_message` directs the user to install it in the template
  image.  Unlike the host `ClaudeCodeHand`, there is no npx fallback.

## Disabled features

The sandbox hand explicitly disables the legacy container wrapping by setting
`_CONTAINER_ENABLED_ENV_VAR` and `_CONTAINER_IMAGE_ENV_VAR` to empty strings.
This prevents double-wrapping (container inside sandbox).

## Source reference

- `src/helping_hands/lib/hands/v1/hand/cli/docker_sandbox_claude.py`
