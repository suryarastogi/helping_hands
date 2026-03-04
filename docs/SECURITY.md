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

## Subprocess execution

CLI-backed hands run external tools as subprocesses:

- Commands are constructed from known safe components (not user-provided shell strings)
- Subprocess environments are explicitly configured (no shell=True with user input)
- Idle timeouts prevent runaway processes (`HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS`)
- Execution tools (`python.run_code`, `bash.run_script`) are opt-in via `--enable-execution`

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

### Gemini CLI approval mode

Gemini CLI supports `--approval-mode` to control edit behavior:

- **`auto_edit`** (default) — automatically applies file edits without prompts
- Other modes require interactive approval, which is incompatible with
  non-interactive execution

## Recommendations for deployment

1. Use read-only `GITHUB_TOKEN` scopes when possible
2. Rotate API keys regularly
3. Review AI-generated code changes before merging
4. Run in Docker for workspace isolation in production
5. Keep `enable_execution` disabled unless explicitly needed
6. Use `workspace-write` sandbox mode for Codex in non-containerized environments
7. Monitor CLI hand heartbeat output to detect stalled processes
