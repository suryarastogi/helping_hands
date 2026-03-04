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

## Recommendations for deployment

1. Use read-only `GITHUB_TOKEN` scopes when possible
2. Rotate API keys regularly
3. Review AI-generated code changes before merging
4. Run in Docker for workspace isolation in production
5. Keep `enable_execution` disabled unless explicitly needed
