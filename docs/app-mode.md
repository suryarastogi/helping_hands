# App Mode & Scheduling

This page covers running `helping_hands` as a server with background workers, including Docker Compose setup, local Celery configuration, and scheduled builds.

## Trigger a run in app mode

App mode enqueues Celery tasks through the FastAPI server and supports `e2e`,
iterative/basic backends, and CLI backends (`codexcli`, `claudecodecli`,
`goose`, `geminicli`, `opencodecli`).

For `codexcli`/`goose` in app mode, rebuild images after pulling latest
changes so the worker image includes required CLIs:

```bash
docker compose build --no-cache
docker compose up
```

For a clean full Docker dev reset/restart:

```bash
docker compose down && docker compose up --build
```

If you update `.env` auth values (like `OPENAI_API_KEY`), recreate running
containers so workers pick up new env vars:

```bash
docker compose up -d --force-recreate server worker beat flower
```

The worker image configures Codex CLI to use `OPENAI_API_KEY` from the
environment (custom model provider in `~/.codex/config.toml`), so no
`codex login` or `auth.json` is required in Docker.
App/worker services in the provided Dockerfile run as a non-root `app` user.

`claudecodecli` in app mode tries `claude -p` first. If `claude` is missing and
`npx` is available, it automatically retries with
`npx -y @anthropic-ai/claude-code`.
For deterministic/offline worker runs, prefer a worker image that preinstalls
Claude Code CLI instead of relying on runtime `npx` download.

## UI features

The built-in UI at `http://localhost:8000/` supports:
- backend selection (`e2e`, `basic-langgraph`, `basic-atomic`, `basic-agent`, `codexcli`, `claudecodecli`, `docker-sandbox-claude`, `goose`, `geminicli`, `opencodecli`)
- model override
- max iterations
- optional PR number
- `no_pr` toggle
- `enable_execution` toggle (python/bash tools; default off)
- `enable_web` toggle (web search/browse tools; default off)
- `use_native_cli_auth` toggle (Codex/Claude: prefer local CLI auth over env keys)
- default editable prompt text: smoke-test prompt that updates `README.md` and
  exercises `@@READ`, `@@FILE`, and (when enabled) `python.run_code`,
  `python.run_script`, `bash.run_script`, `web.search`, and `web.browse`
- JS polling monitor via `/tasks/{task_id}`
- dynamic current-task discovery via `/tasks/current` (Flower when configured,
  plus Celery inspect fallback)
- no-JS fallback monitor via `/monitor/{task_id}` (auto-refresh)
- fixed-size monitor cells for task/status, updates, and payload panels (scrolls inside each cell)
- **World view**: toggle between "classic" and "world" dashboard views; world view displays an isometric agent office visualization where active workers appear at desks
- **Keyboard navigation** (world view only): use arrow keys or WASD to move the player character around the office; WASD keys are disabled when typing in input fields to allow normal text entry

<p align="center">
  <img src="../media/FrontEndReact.png" alt="React frontend — agent office world view" width="800" />
</p>

## curl examples

```bash
# Visit the built-in UI in your browser:
# http://localhost:8000/

# Enqueue a build task
curl -sS -X POST "http://localhost:8000/build" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "suryarastogi/helping_hands",
    "prompt": "CI integration run: update PR on master",
    "backend": "e2e"
  }'

# Check task status (replace <TASK_ID> from /build response)
curl -sS "http://localhost:8000/tasks/<TASK_ID>"

# List current active/queued task UUIDs
curl -sS "http://localhost:8000/tasks/current"

# Open HTML monitor page (auto-refresh, no JS required)
# http://localhost:8000/monitor/<TASK_ID>

# Example iterative run (same options as CLI)
curl -sS -X POST "http://localhost:8000/build" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "suryarastogi/helping_hands",
    "prompt": "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no.",
    "backend": "basic-langgraph",
    "model": "gpt-5.2",
    "max_iterations": 4,
    "no_pr": true
  }'

# Example codexcli run in app mode
curl -sS -X POST "http://localhost:8000/build" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "suryarastogi/helping_hands",
    "prompt": "Implement one small safe improvement",
    "backend": "codexcli",
    "model": "gpt-5.2"
  }'

# Example claudecodecli run in app mode
curl -sS -X POST "http://localhost:8000/build" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "suryarastogi/helping_hands",
    "prompt": "Implement one small safe improvement",
    "backend": "claudecodecli",
    "model": "anthropic/claude-sonnet-4-5"
  }'

# Example goose run in app mode
curl -sS -X POST "http://localhost:8000/build" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "suryarastogi/helping_hands",
    "prompt": "Implement one small safe improvement",
    "backend": "goose"
  }'

# Example geminicli run in app mode
curl -sS -X POST "http://localhost:8000/build" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "suryarastogi/helping_hands",
    "prompt": "Implement one small safe improvement",
    "backend": "geminicli"
  }'

# Example opencodecli run in app mode
curl -sS -X POST "http://localhost:8000/build" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "suryarastogi/helping_hands",
    "prompt": "Implement one small safe improvement",
    "backend": "opencodecli",
    "model": "litellm/claude-sonnet-4-6"
  }'
```

Optional one-liner (requires `jq`) to enqueue and poll:

```bash
TASK_ID=$(curl -sS -X POST "http://localhost:8000/build" -H "Content-Type: application/json" -d '{"repo_path":"suryarastogi/helping_hands","prompt":"CI integration run: update PR on master"}' | jq -r .task_id); while true; do curl -sS "http://localhost:8000/tasks/$TASK_ID"; echo; sleep 2; done
```

If UI submit appears to enqueue but you do not see repeated `/tasks/<id>` requests
in logs (common when browser JS is blocked), use `/monitor/<id>`; that endpoint
refreshes server-side without client-side JavaScript and keeps monitor card sizes
stable while polling.

## Local Celery setup (Dockerized data services)

Run `server`/`worker`/`beat`/`flower` locally with `uv`, while keeping only
`postgres` and `redis` in Docker:

```bash
# 1) Prepare env + install server deps
cp .env.example .env
uv sync --extra server

# 2) Start data services only
docker compose up -d postgres redis

# 3) Start local app/celery processes (background)
./scripts/run-local-stack.sh start

# 4) Check status / logs
./scripts/run-local-stack.sh status
./scripts/run-local-stack.sh logs worker
```

Useful commands:

```bash
# Tail all local process logs
./scripts/run-local-stack.sh logs

# Restart local processes
./scripts/run-local-stack.sh restart

# Stop local processes
./scripts/run-local-stack.sh stop

# Stop dockerized data services
docker compose stop postgres redis
```

Notes:

- Script path: `scripts/run-local-stack.sh`
- Process logs/PIDs: `runs/local-stack/logs` and `runs/local-stack/pids`
- If `.env` uses docker hostnames like `redis://redis:6379/0`, the script
  automatically rewrites them to `localhost` for local runs.
- To keep docker hostnames unchanged, set `HH_LOCAL_STACK_KEEP_DOCKER_HOSTS=1`.

## Compose env defaults

`compose.yaml` now sets default in-network Celery/Redis URLs for all app-mode
services if they are not set in `.env`:

- `REDIS_URL=redis://redis:6379/0`
- `CELERY_BROKER_URL=redis://redis:6379/0`
- `CELERY_RESULT_BACKEND=redis://redis:6379/1`
- `HELPING_HANDS_FLOWER_API_URL=http://flower:5555` (server-side `/tasks/current`
  discovery path)

## Scheduling

App mode supports two schedule types for recurring builds:

### Cron schedules (fixed-time)

Fires at the times defined by a standard cron expression (e.g. `0 0 * * *` for
midnight daily) using RedBeat.  Runs **may overlap** if a previous build hasn't
finished when the next trigger fires.

### Interval schedules (non-concurrent)

Runs a build, waits for it to complete, then waits an additional N seconds
before starting the next one.  This guarantees **no overlap** — each run has
exclusive access to the repo.  The chain is:
`build → complete → wait interval → build → …`

Disabling or deleting an interval schedule stops the chain immediately (pending
tasks are revoked and `build_feature` checks the enabled flag at startup).

### PR number semantics

When a **PR number is specified** on a schedule (or one-off build):

1. The hand checks out that PR's branch and performs its updates there.
2. It attempts to push directly to the PR branch.
3. If the push is rejected (e.g. diverged history), a **follow-up PR** is
   created targeting the original PR's branch.
4. The schedule **retains the original PR number** — subsequent runs keep
   targeting the same PR, not the follow-up.

When **no PR number is specified**:

1. The first build creates a new PR.
2. That PR number is **auto-persisted** back to the schedule.
3. All subsequent runs push to that same PR.
4. Once set (either by the user or by auto-persist), the PR number is never
   silently overwritten.
