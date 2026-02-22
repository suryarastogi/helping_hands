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
- App UI (`/`) can submit runs with backend/model/max-iteration/no-pr options
  and monitor live task updates via `/tasks/{task_id}`.
- CLI mode: CLI invokes the hand directly (index-only, E2E mode, or iterative basic backends).
- `E2EHand` is the minimal concrete hand used to validate the full
  clone/edit/commit/push/PR lifecycle.
- Optional `pr_number` lets the hand resume/update an existing PR branch.
- Basic iterative backends (`basic-langgraph`, `basic-atomic`, `basic-agent`)
  stream multi-step output and, by default, attempt a final commit/push/PR step
  unless disabled via `--no-pr`.
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

## CLI examples

```bash
# basic-langgraph
uv run helping-hands "suryarastogi/helping_hands" --backend basic-langgraph --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# basic-atomic
uv run helping-hands "suryarastogi/helping_hands" --backend basic-atomic --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# basic-agent
uv run helping-hands "suryarastogi/helping_hands" --backend basic-agent --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# e2e (new PR)
uv run helping-hands "suryarastogi/helping_hands" --e2e --prompt "CI integration run: update PR on master"

# e2e (update existing PR #1)
uv run helping-hands "suryarastogi/helping_hands" --e2e --pr-number 1 --prompt "CI integration run: update PR on master"
```
