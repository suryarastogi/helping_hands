# Security

Security considerations for helping_hands deployments and development.

## Path traversal prevention

All file operations route through `resolve_repo_target()` in
`lib/meta/tools/filesystem.py`. This function:

1. Resolves the repo root to an absolute path
2. Normalizes the relative path (strips `./`, converts backslashes)
3. Rejects absolute paths and empty paths
4. Verifies the resolved target is a descendant of the repo root

This prevents `../../etc/passwd`-style traversal attacks from AI-generated
file paths.

## Token authentication

Git push operations use token-authenticated HTTPS remotes. Interactive
credential prompts are explicitly disabled (`GIT_TERMINAL_PROMPT=0`,
`GIT_ASKPASS=`). This prevents:

- Blocking on credential dialogs in automated/worker environments
- Accidental credential leakage through OS keychain prompts

## API key handling

- API keys are loaded from environment variables or `.env` files
- Keys are never logged, committed, or included in PR descriptions
- `--use-native-cli-auth` strips API keys from subprocess environments
  when delegating to external CLI tools
- `.env` files are in `.gitignore`
- Error messages from env var parsing (e.g. `_base_command()`) redact raw
  values to prevent accidental token/secret leakage in logs

## Subprocess execution

CLI-backed hands run external tools as subprocesses:

- Commands are constructed from known safe components (not user-provided shell strings)
- Subprocess environments are explicitly configured (no shell=True with user input)
- Idle timeouts prevent runaway processes (`HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS`)
- Git read subprocesses (`_run_git_read`, `_repo_has_changes`) enforce a
  `_GIT_READ_TIMEOUT_S` (30s) timeout to prevent indefinite blocking on
  hung git processes
- Execution tools (`python.run_code`, `bash.run_script`) are opt-in via `--enable-execution`

## Clone URL validation

`_github_clone_url()` (in both CLI and Celery) validates the repo spec
matches `owner/repo` format via `_validate_repo_spec()` before embedding
it into a URL. This prevents malformed or empty strings from producing
invalid git clone URLs.

## Docker security

- App/worker containers run as non-root `app` user
- Only the target repo is bind-mounted in container mode
- Network access is scoped to service-to-service within Compose network

## Execution sandboxing

### Codex CLI sandbox modes

Codex CLI supports `--sandbox` to restrict filesystem access:

- **`workspace-write`** (default outside Docker) — read/write within the repo,
  read-only elsewhere. Safe for most tasks.
- **`danger-full-access`** (default inside Docker) — unrestricted filesystem.
  Used when the container itself provides isolation.
- **`read-only`** — no writes allowed. Useful for analysis-only tasks.

The sandbox mode is configured via `HELPING_HANDS_CODEX_SANDBOX_MODE` or
auto-detected based on whether `/.dockerenv` exists.

### Claude Code permissions

Claude Code CLI supports `--dangerously-skip-permissions` to run without
interactive approval prompts. helping_hands enables this by default for
non-interactive execution, with safety checks:

- **Root detection**: The flag is automatically omitted when running as root
  (`os.geteuid() == 0`), because Claude Code rejects it under root privileges.
- **Disable via env**: Set `HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS=0`
  to require interactive approval (not recommended for automated runs).
- **Permission prompt detection**: If the CLI output contains permission
  approval markers, helping_hands raises a clear error rather than silently
  producing no changes.

### Container isolation for CLI hands

Codex and Claude Code hands support running inside Docker containers:

- Enable with `HELPING_HANDS_{BACKEND}_CONTAINER=1`
- Specify image with `HELPING_HANDS_{BACKEND}_CONTAINER_IMAGE`
- Only the target repo directory is bind-mounted at `/workspace`
- API keys are passed as explicit `-e` flags (not inherited from host env)
- The container runs with `--rm` (auto-cleanup) and `-i` (stdin for
  subprocess communication)

This provides an additional isolation layer: even if the AI tool generates
malicious commands, they execute within a disposable container with limited
filesystem access.

### Docker Desktop sandbox isolation

`DockerSandboxClaudeCodeHand` runs Claude Code inside a Docker Desktop
microVM sandbox (`docker sandbox create` / `docker sandbox exec`), providing
stronger isolation than standard containers:

- **MicroVM boundary** — the sandbox runs in a lightweight VM, not just a
  namespace-isolated container.  Filesystem, network, and process trees are
  fully separated from the host.
- **Workspace sync** — only the target repo directory is synced into the
  sandbox at the same absolute path.  No other host directories are exposed.
- **Auto-cleanup** — by default, the sandbox is destroyed (`docker sandbox stop`
  + `docker sandbox rm`) after execution.  Disable with
  `HELPING_HANDS_DOCKER_SANDBOX_CLEANUP=0` to inspect sandbox state post-run.
- **Name isolation** — sandbox names are auto-generated from the hand UUID and
  sanitized to DNS-compatible labels, preventing collisions across concurrent
  runs.
- **Plugin requirement** — requires Docker Desktop with the `docker sandbox`
  CLI plugin.  If the plugin is unavailable, creation fails with a clear error
  rather than falling back to unsandboxed execution.
- **Environment forwarding** — API keys are passed as explicit `-e` flags to
  `docker sandbox exec`, not inherited from the host environment.

### Gemini CLI approval mode

Gemini CLI supports `--approval-mode` to control edit behavior:

- **`auto_edit`** (default) — automatically applies file edits without prompts
- Other modes require interactive approval, which is incompatible with
  non-interactive execution

## Iterative hand security boundaries

### BasicLangGraphHand / BasicAtomicHand

Iterative hands (`basic-langgraph`, `basic-atomic`) execute AI-provider API
calls directly rather than spawning external CLI subprocesses. Security
considerations differ from CLI-backed hands:

- **No subprocess sandboxing** — these hands run in-process. File operations
  route through `resolve_repo_target()` (same path-traversal protection as CLI
  hands), but there is no OS-level sandbox separating the AI loop from the
  host process.
- **Tool dispatch** — when `--tools execution` is enabled, `@@TOOL:` blocks
  invoke `run_python_code` / `run_bash_script` as real subprocesses. These are
  **not** sandboxed by default; treat `--tools execution` as elevated privilege.
- **Network access** — iterative hands make outbound HTTPS calls to AI provider
  APIs. When `--tools web` is enabled, `search_web` and `browse_url` make
  additional outbound requests. No egress filtering is applied.
- **Context window** — AI-generated `@@FILE` / `@@READ` operations are bounded
  by `resolve_repo_target()`, preventing reads outside the repo root.

**Mitigation**: Run iterative hands inside Docker (app mode) to add container
isolation. In local CLI mode, avoid `--tools execution` on untrusted repos.

## Recommendations for deployment

1. Use read-only `GITHUB_TOKEN` scopes when possible
2. Rotate API keys regularly
3. Review AI-generated code changes before merging
4. Run in Docker for workspace isolation in production
5. Keep `enable_execution` disabled unless explicitly needed
6. Use `workspace-write` sandbox mode for Codex in non-containerized environments
7. Monitor CLI hand heartbeat output to detect stalled processes
