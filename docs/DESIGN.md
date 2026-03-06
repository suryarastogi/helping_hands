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

- **Docker Sandbox Claude** (`docker_sandbox_claude.py`): Extends `ClaudeCodeHand`
  to run inside a Docker Desktop microVM sandbox (`docker sandbox create` /
  `docker sandbox exec`).  The workspace directory is synced at the same absolute
  path.  Sandbox names are auto-generated and cached per instance.  Cleanup is
  controlled by `HELPING_HANDS_DOCKER_SANDBOX_CLEANUP` (default: auto-remove).
  Requires Docker Desktop with the `docker sandbox` CLI plugin.

### PR description and commit message generation

The `pr_description` module (`hands/v1/hand/pr_description.py`) generates rich
PR titles/bodies and commit messages by invoking a CLI tool (e.g. `claude -p`)
against the git diff.  Key design choices:

- **Opt-in with graceful fallback** — when no CLI is available or generation
  fails, the system falls back to heuristic message derivation from the task
  prompt/summary.
- **Diff truncation** — diffs are capped at configurable limits (12k chars for
  PR descriptions, 8k for commit messages) to stay within model context.
- **Structured output parsing** — CLI output must contain `PR_TITLE:` /
  `PR_BODY:` or `COMMIT_MSG:` markers; unparseable output is silently skipped.
- **Environment-controlled** — timeout, diff limit, and disable toggle are all
  configurable via `HELPING_HANDS_*` env vars.

### Scheduled task management

The `schedules` module (`server/schedules.py`) provides cron-based recurring
task execution using RedBeat for Redis-backed persistence.  Key design choices:

- **Dataclass-driven** — `ScheduledTask` is a plain dataclass serialized to/from
  JSON in Redis.  No ORM or database schema required.
- **Dual storage** — schedule metadata lives in Redis keys
  (`helping_hands:schedule:meta:{id}`); the actual cron trigger lives in RedBeat's
  scheduler entries.  The two are kept in sync by `ScheduleManager` CRUD methods.
- **Lazy dependency checks** — `redbeat` and `croniter` are optional imports
  guarded by `_check_redbeat()` / `_check_croniter()`.  The rest of the server
  works without them; only schedule endpoints require the extras.
- **Cron presets** — common patterns (`daily`, `hourly`, `weekdays`, etc.) are
  resolved from `CRON_PRESETS` before validation, so users can pass human-readable
  names instead of raw cron strings.
- **Trigger-now** — `trigger_now()` dispatches an immediate Celery task using the
  schedule's saved parameters, recording the run in metadata.

### Health checks and server config

The FastAPI server exposes `/health` (basic liveness) and `/health/services`
(per-service connectivity) endpoints.  Each backing service has a dedicated
probe function:

| Probe | Mechanism | Returns |
|---|---|---|
| `_check_redis_health` | `redis.Redis.from_url(...).ping()` with 2 s timeout | `"ok"` / `"error"` |
| `_check_db_health` | `psycopg2.connect(DATABASE_URL)` with 3 s timeout | `"ok"` / `"error"` / `"na"` (no `DATABASE_URL`) |
| `_check_workers_health` | `celery_app.control.inspect(timeout=2).ping()` | `"ok"` / `"error"` |

All probes catch broad `Exception` so a single failing service never crashes the
health endpoint.  Dependencies (`redis`, `psycopg2`) are imported locally inside
the probe functions to keep them soft-optional.

`_is_running_in_docker()` detects container environments via `/.dockerenv` file
presence or the `HELPING_HANDS_IN_DOCKER` env var.  The `/config` endpoint
exposes this to the frontend so it can default `use_native_cli_auth` accordingly.

Flower integration (`_fetch_flower_current_tasks`) is also soft-optional:
when `HELPING_HANDS_FLOWER_API_URL` is unset the helper returns an empty list.
When configured, it merges Flower task data with Celery inspect results via
`_upsert_current_task`, preferring the highest-priority status and merging
source labels.

### Finalization

Commit/push/PR logic is centralized in the `Hand` base class so all backends
share the same branch naming, token auth, and PR body generation.

## Anti-patterns to avoid

- **Global state** — No module-level caches or singletons
- **Cross-layer imports** — CLI/server should not import each other's internals
- **Monolithic files** — Keep hand implementations in separate modules
- **Implicit auth** — Always use explicit token-based push, never OS credential prompts
