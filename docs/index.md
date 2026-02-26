# helping_hands

**AI-powered repo builder** — point it at a codebase, describe what you want, and let an AI agent help you build and ship features.

For full project details, see the [README](https://github.com/suryarastogi/helping_hands#readme).

## API Reference

Browse the auto-generated docs from source:

- **lib** — Core library: [config](api/lib/config.md), [repo](api/lib/repo.md), [github](api/lib/github.md), [ai providers package](api/lib/ai_providers.md), [hands v1 package](api/lib/hands/v1/hand.md), [meta tools package](api/lib/meta/tools.md), [meta tools.filesystem](api/lib/meta/tools/filesystem.md)
- **cli** — CLI entry point: [main](api/cli/main.md)
- **server** — App mode: [app](api/server/app.md), [celery_app](api/server/celery_app.md), [mcp_server](api/server/mcp_server.md)

## Runtime flow

- Server mode: server enqueues a hand task, then the hand executes.
- App UI (`/`) can submit runs with backend/model/max-iterations/no-pr options.
- App UI defaults prompt input to a smoke-test `README.md` updater that
  exercises `@@READ`, `@@FILE`, and (when enabled) `python.run_code`,
  `python.run_script`, `bash.run_script`, `web.search`, and `web.browse`
  (editable).
- Execution and web tools are opt-in per run (`enable_execution`, `enable_web`).
- Native CLI auth is opt-in per run (`use_native_cli_auth`) and currently
  applies to `codexcli`/`claudecodecli` by stripping provider API key env vars
  from subprocess execution.
- JS monitor path polls `/tasks/{task_id}` for live status/updates.
- No-JS fallback path redirects to `/monitor/{task_id}` (auto-refresh HTML monitor).
- Monitor views use fixed-size task/status/update/payload cells so layout remains
  stable while polling; long content scrolls inside each cell.
- CLI mode: CLI invokes the hand directly (index-only, E2E mode, or iterative basic backends).
- `E2EHand` is the minimal concrete hand used to validate the full
  clone/edit/commit/push/PR lifecycle.
- Optional `pr_number` lets the hand resume/update an existing PR branch.
- Basic iterative backends (`basic-langgraph`, `basic-atomic`, `basic-agent`)
  stream multi-step output and, by default, attempt a final commit/push/PR step
  unless disabled via `--no-pr`.
- When `enable_execution` is set, PR finalization runs `uv run pre-commit run --all-files`
  (auto-fix + validation retry) before commit/push.
- CLI-driven backends (`codexcli`, `claudecodecli`, `goose`) run a two-phase flow:
  initialize/learn first, then execute the user task.
- `codexcli` passes `--model gpt-5.2` by default when model is unset/default.
- `codexcli` sets sandbox mode automatically:
  - host: `workspace-write`
  - container: `danger-full-access` (to avoid landlock failures)
- override with `HELPING_HANDS_CODEX_SANDBOX_MODE`.
- `codexcli` adds `--skip-git-repo-check` by default for non-interactive runs.
- `claudecodecli` uses `claude -p` by default and supports command override via
  `HELPING_HANDS_CLAUDE_CLI_CMD`.
- If `claude` is missing and `npx` is available, `claudecodecli` retries with
  `npx -y @anthropic-ai/claude-code`.
- `claudecodecli` adds `--dangerously-skip-permissions` by default in
  non-interactive non-root mode (disable with
  `HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS=0`).
- If Claude rejects that flag under root/sudo, backend retries automatically
  without the flag.
- If Claude asks for interactive write approval and no edits are applied after
  retry, the run fails with a clear error instead of returning success.
- For edit-intent prompts, `claudecodecli` auto-runs one follow-up apply pass
  when the first task pass reports no repository file changes.
- CLI subprocess controls (all CLI backends):
  - `HELPING_HANDS_CLI_IO_POLL_SECONDS` (default `2`)
  - `HELPING_HANDS_CLI_HEARTBEAT_SECONDS` (default `20`)
  - `HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS` (default `300`)
- Basic iterative hands preload iteration-1 context with `README.md`/`AGENT.md`
  (when present) and a bounded-depth repo tree snapshot.
- Model selection resolves through `lib.ai_providers` wrappers, including
  `provider/model` forms, before backend-specific model adaptation.
- Iterative/basic hands use shared system file tooling from `lib.meta.tools`
  for repo-safe reads/writes and path validation.
- MCP now exposes filesystem tools backed by the same layer:
  `read_file`, `write_file`, `mkdir`, and `path_exists`.
- CI test runs include coverage reporting and upload `coverage.xml` to Codecov
  from the Python 3.12 job.
- Compose defaults include in-network Redis/Celery URLs for app-mode services
  (`REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).

## Codex backend requirements

- `codex` CLI installed and on `PATH`.
- Authenticated codex session in your shell (`codex login`) or equivalent key-based setup.
- `GITHUB_TOKEN` or `GH_TOKEN` set if you want final commit/push/PR creation.
- Access to the model you request; if your codex default model is unavailable, pass `--model gpt-5.2`.
- Optional container mode is available via:
  - `HELPING_HANDS_CODEX_CONTAINER=1`
  - `HELPING_HANDS_CODEX_CONTAINER_IMAGE=<image-with-codex-cli>`
- You can disable automatic `--skip-git-repo-check` with:
  - `HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK=0`
- App mode supports `codexcli`, `claudecodecli`, and `goose`; ensure the Celery worker
  environment has corresponding CLIs installed and authenticated.
- Docker app/worker images in this repo install `@openai/codex` and Goose CLI; rebuild images after updates.

Quick check:

```bash
codex exec --model gpt-5.2 "Reply with READY and one sentence."
```

## Claude Code backend requirements

- `claude` CLI on `PATH`, or `npx` available for fallback execution.
- Auth configured for CLI execution (typically `ANTHROPIC_API_KEY`).
- `GITHUB_TOKEN` or `GH_TOKEN` set if you want final commit/push/PR creation.
- Optional container mode:
  - `HELPING_HANDS_CLAUDE_CONTAINER=1`
  - `HELPING_HANDS_CLAUDE_CONTAINER_IMAGE=<image-with-claude-cli>`
- App mode supports `claudecodecli`; default Docker app/worker images do not
  preinstall Claude Code CLI binary but do include `npx` fallback support.
- The bundled Docker app/worker images run as a non-root `app` user by default.
- If relying on `npx` fallback in app mode, worker runtime needs network access
  to download `@anthropic-ai/claude-code`.

## Goose backend requirements

- `goose` CLI on `PATH`.
- `GH_TOKEN` or `GITHUB_TOKEN` must be set.
- `goose run` calls include `--with-builtin developer` by default (or it is
  auto-injected) so file editing/shell tools are available.
- `GOOSE_PROVIDER`/`GOOSE_MODEL` are auto-derived from `HELPING_HANDS_MODEL`
  (fallback: `ollama` + `llama3.2:latest`) so `goose configure` is not required.
- For remote Ollama instances, set `OLLAMA_HOST`
  (for example `http://192.168.1.143:11434`).
- Runtime mirrors the available token into both `GH_TOKEN` and `GITHUB_TOKEN`
  for Goose subprocesses.
- Local GitHub auth fallback is disabled for Goose backend runs.

## CLI examples

```bash
# basic-langgraph
uv run helping-hands "suryarastogi/helping_hands" --backend basic-langgraph --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# basic-atomic
uv run helping-hands "suryarastogi/helping_hands" --backend basic-atomic --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# basic-agent
uv run helping-hands "suryarastogi/helping_hands" --backend basic-agent --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# codexcli
uv run helping-hands "suryarastogi/helping_hands" --backend codexcli --model gpt-5.2 --prompt "Implement one small safe improvement"

# claudecodecli
uv run helping-hands "suryarastogi/helping_hands" --backend claudecodecli --model anthropic/claude-sonnet-4-5 --prompt "Implement one small safe improvement"

# goose
uv run helping-hands "suryarastogi/helping_hands" --backend goose --prompt "Implement one small safe improvement"

# e2e (new PR)
uv run helping-hands "suryarastogi/helping_hands" --e2e --prompt "CI integration run: update PR on master"

# e2e (update existing PR #1)
uv run helping-hands "suryarastogi/helping_hands" --e2e --pr-number 1 --prompt "CI integration run: update PR on master"
```
