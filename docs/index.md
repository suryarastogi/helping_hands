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
- App UI defaults prompt input to `Update README.md` (editable).
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
- `codexcli` backend runs a two-phase CLI workflow:
  initialization/learning pass, then task execution pass.
- `codexcli` passes `--model gpt-5.2` by default when model is unset/default.
- `codexcli` sets sandbox mode automatically:
  - host: `workspace-write`
  - container: `danger-full-access` (to avoid landlock failures)
- override with `HELPING_HANDS_CODEX_SANDBOX_MODE`.
- `codexcli` adds `--skip-git-repo-check` by default for non-interactive runs.
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
- App mode supports `codexcli`; ensure the Celery worker environment has `codex` installed and authenticated.
- Docker app/worker images in this repo install `@openai/codex`; rebuild images after updates.

Quick check:

```bash
codex exec --model gpt-5.2 "Reply with READY and one sentence."
```

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

# e2e (new PR)
uv run helping-hands "suryarastogi/helping_hands" --e2e --prompt "CI integration run: update PR on master"

# e2e (update existing PR #1)
uv run helping-hands "suryarastogi/helping_hands" --e2e --pr-number 1 --prompt "CI integration run: update PR on master"
```
