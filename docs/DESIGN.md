# Design Philosophy

Core design patterns and principles for helping_hands.

## Guiding principles

1. **Plain data between layers** — Modules communicate through dicts and
   dataclasses. No tight coupling between config, repo, hands, and entry points.

2. **Streaming by default** — AI responses stream to the caller as they arrive.
   No buffering full responses unless explicitly needed.

3. **Explicit configuration** — No module-level singletons. `Config` is loaded
   once and threaded through function calls.

4. **Path safety** — All filesystem operations route through
   `meta/tools/filesystem.py` with `resolve_repo_target()` preventing
   path traversal outside the repo root.

5. **Minimal side effects** — Hands attempt commit/push/PR by default, but
   all side effects can be disabled (`--no-pr`). Execution and web tools
   are opt-in.

## Patterns

### Hand abstraction

The `Hand` base class defines the contract: `run()` for sync, `stream()` for
async iteration. Implementations are split into separate modules under
`hands/v1/hand/` to prevent monolithic growth.

### Provider resolution

Model strings like `gpt-5.2` or `anthropic/claude-sonnet-4-5` resolve through
the `ai_providers/` layer. Each provider wraps its SDK with a common interface
and lazy initialization.

### Two-phase CLI hands

CLI-backed hands (`codex`, `claude`, `goose`, `gemini`, `opencode`) run two
subprocess phases: (1) initialize/learn the repo, (2) execute the task.
This separation gives the external CLI tool repo context before acting.

Each backend customizes the shared `_TwoPhaseCLIHand` base through hook methods:

| Hook method | Purpose | Example backends |
|---|---|---|
| `_apply_backend_defaults()` | Inject CLI-specific flags before execution | All CLI hands |
| `_retry_command_after_failure()` | Return a modified command to retry on known errors | Claude (root permission), Gemini (model not found) |
| `_build_failure_message()` | Parse CLI output into actionable error messages | All CLI hands |
| `_fallback_command_when_not_found()` | Try alternate command when primary is missing | Claude (`npx` fallback) |
| `_resolve_cli_model()` | Filter or transform model names for the target CLI | Claude (rejects GPT models), OpenCode (preserves provider/model) |

#### Backend-specific behaviors

- **Claude Code** (`claude.py`): Injects `--dangerously-skip-permissions` (disabled
  for root), uses `--output-format stream-json` with `_StreamJsonEmitter` for
  structured progress parsing, falls back to `npx @anthropic-ai/claude-code` when
  `claude` binary is not found. Retries without skip-permissions on root-privilege
  errors. Detects write-permission prompt markers to surface non-interactive failures.

- **Codex** (`codex.py`): Injects `--sandbox` mode (defaults to `workspace-write`,
  switches to `danger-full-access` inside Docker containers) and
  `--skip-git-repo-check`. Normalizes bare `codex` command to `codex exec`.

- **Gemini** (`gemini.py`): Injects `--approval-mode auto_edit`. Requires
  `GEMINI_API_KEY` at subprocess env build time. Retries with `--model` stripped
  when the CLI reports model-not-found errors. Extracts model names from
  `models/<name>` patterns in error output.

- **Goose** (`goose.py`): Normalizes provider names (e.g. `gemini` to `google`),
  infers provider from model name prefixes, normalizes `OLLAMA_HOST` URLs.

- **OpenCode** (`opencode.py`): Preserves `provider/model` format for model
  resolution (no provider inference needed). Minimal hook surface.

### Finalization

Commit/push/PR logic is centralized in the `Hand` base class so all backends
share the same branch naming, token auth, and PR body generation.

## Anti-patterns to avoid

- **Global state** — No module-level caches or singletons
- **Cross-layer imports** — CLI/server should not import each other's internals
- **Monolithic files** — Keep hand implementations in separate modules
- **Implicit auth** — Always use explicit token-based push, never OS credential prompts
