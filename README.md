<p align="center">
  <img src="media/banner.png" alt="helping_hands" />
</p>

<p align="center">
  <a href="https://codecov.io/gh/suryarastogi/helping_hands">
    <img src="https://codecov.io/gh/suryarastogi/helping_hands/graph/badge.svg" alt="Coverage" />
  </a>
</p>

---

**Last updated:** March 30, 2026

## What is this?

`helping_hands` is a Python tool that takes a git repository as input, understands its structure and conventions, and collaborates with you to add features, fix bugs, and evolve the codebase using AI. It can run in **CLI mode** (interactive in the terminal) or **app mode** (server with background workers).

### Modes

- **CLI mode** (default) — Run `helping-hands <repo>` (local path) or `helping-hands <owner/repo>` (auto-clones to a temp workspace, cleaned up on exit). You can index only, or run iterative backends plus external-CLI backends with streamed output:
  - iterative: `basic-langgraph` (requires `--extra langchain`), `basic-atomic` / `basic-agent` (require `--extra atomic`)
  - external CLI: `codexcli`, `claudecodecli`, `docker-sandbox-claude`, `goose`, `geminicli`, `opencodecli`, `devincli`
- **App mode** — Runs a FastAPI server plus a worker stack (Celery, Redis, Postgres) so jobs run asynchronously and on a schedule (cron). Includes Flower for queue monitoring. Use when you want a persistent service, queued or scheduled repo-building tasks, or a UI.

### Execution flow

- **Server mode**: `server -> enqueue task -> worker executes selected hand -> status`
- **CLI mode**: `cli -> hand executes`

For asynchronous runs, the hand UUID is the Celery task ID. For synchronous
runs, UUIDs are generated in-hand as needed.

- `E2EHand` uses `{hand_uuid}/git/{repo}` workspace layout and supports
  new PR creation plus resume/update via `--pr-number`.
- Basic iterative hands (`basic-langgraph`, `basic-atomic`) operate on the
  target repo context and, by default, attempt a final commit/push/PR step.
  Disable with `--no-pr`.
- Basic iterative hands preload startup context on iteration 1 by including
  `README.md`/`AGENT.md` (when present) and a bounded repository tree snapshot.
- Iterative basic hands can request file contents using `@@READ: path` and
  apply edits using `@@FILE` blocks in-model.
- System filesystem actions for hands (path-safe read/write/mkdir checks) are
  centralized in `lib/meta/tools/filesystem.py`.
- Provider-level wrappers and model/env defaults are centralized in
  `lib/ai_providers/` (`openai`, `anthropic`, `google`, `litellm`, `ollama`).
- Hands resolve model strings through provider wrappers (including
  `provider/model` forms) before adapting to backend-specific model clients.
- Push uses token-authenticated GitHub remote configuration and disables
  interactive credential prompts.
- When `enable_execution` is on, final PR flow runs `uv run pre-commit run --all-files`
  (auto-fix + validation retry) before commit/push.

### Key ideas

- **Repo-aware**: Clones or reads a local repo, indexes the file tree, and builds context so the AI understands what it's working with.
- **Conversational building**: Describe what you want in plain language. The agent proposes changes, writes code, and iterates with you.
- **Convention-respectful**: Learns the repo's patterns (naming, structure, style) and follows them in generated code.
- **Self-improving guidance**: Ships with an `AGENT.md` file that the agent updates over time as it learns your preferences for tone, style, and design.
- **E2E validation hand**: `E2EHand` is a minimal concrete hand used to test
  the full clone/edit/commit/push/PR flow.
- **Iterative basic hands**: `basic-langgraph` and `basic-atomic` run
  stepwise implementation loops with live streaming, interruption, startup
  bootstrap context (README/AGENT/tree snapshot), and optional final PR
  creation.

## Quick start

Get from zero to your first AI-driven code change in three steps.
Requires **Python 3.12+** and [uv](https://docs.astral.sh/uv/).

### 1. Install

```bash
git clone git@github.com:suryarastogi/helping_hands.git
cd helping_hands
uv sync --dev
```

### 2. Set API keys

Export at least one AI provider key:

```bash
export OPENAI_API_KEY="sk-..."        # for GPT models
# — or —
export ANTHROPIC_API_KEY="sk-ant-..." # for Claude models
# — or —
export GOOGLE_API_KEY="..."           # for Gemini models
```

Verify your environment is ready:

```bash
uv run helping-hands doctor
```

### 3. Run your first task

Try the bundled example — a tiny Python package with a deliberate bug:

```bash
cd examples/fix-greeting
bash run.sh   # runs helping-hands with --no-pr (no GitHub access needed)
```

Or point at any local repo:

```bash
uv run helping-hands ./my-project --backend basic-langgraph --model gpt-5.2 \
  --prompt "Add type hints to utils.py" --no-pr
```

### More examples

```bash
# Iterative backends (owner/repo is auto-cloned)
uv run helping-hands owner/repo --backend basic-langgraph --model gpt-5.2 --prompt "Implement X" --max-iterations 4
uv run helping-hands owner/repo --backend basic-atomic --model gpt-5.2 --prompt "Implement X" --max-iterations 4
uv run helping-hands owner/repo --backend basic-agent --model gpt-5.2 --prompt "Implement X" --max-iterations 4

# CLI backends (two-phase: initialize repo context, then execute task)
uv run helping-hands owner/repo --backend codexcli --model gpt-5.2 --prompt "Implement X"
uv run helping-hands owner/repo --backend claudecodecli --model anthropic/claude-sonnet-4-5 --prompt "Implement X"
uv run helping-hands owner/repo --backend geminicli --prompt "Implement X"
uv run helping-hands owner/repo --backend goose --prompt "Implement X"
uv run helping-hands owner/repo --backend opencodecli --model litellm/claude-sonnet-4-6 --prompt "Implement X"
uv run helping-hands owner/repo --backend devincli --prompt "Implement X"

# Force native CLI auth (ignore provider API key env vars)
uv run helping-hands owner/repo --backend codexcli --model gpt-5.2 --use-native-cli-auth --prompt "Implement X"

# Disable final commit/push/PR step
uv run helping-hands owner/repo --backend basic-langgraph --model gpt-5.2 --prompt "Implement X" --no-pr

# Enable execution/web tools for iterative backends
uv run helping-hands owner/repo --backend basic-langgraph --enable-execution --enable-web --prompt "Run the smoke test prompt"

# E2E mode against a GitHub repo
uv run helping-hands owner/repo --e2e --prompt "E2E smoke test"
uv run helping-hands owner/repo --e2e --pr-number 1 --prompt "Update PR 1"

# App mode (Docker Compose)
cp .env.example .env  # edit as needed
docker compose up --build

# React frontend
cd frontend && npm install && npm run dev
```

### Trigger a run in app mode

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

### Local Celery setup (Dockerized data services)

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
  <img src="media/FrontEndReact.png" alt="React frontend — agent office world view" width="800" />
</p>

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

## Project structure

```
helping_hands/
├── src/helping_hands/        # Main package
│   ├── lib/                  # Core library (config, repo, github, hands, meta tools)
│   │   ├── config.py
│   │   ├── repo.py
│   │   ├── github.py
│   │   ├── ai_providers/     # Provider wrappers + API key env/model defaults
│   │   │   ├── __init__.py
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   ├── google.py
│   │   │   ├── litellm.py
│   │   │   ├── ollama.py
│   │   │   └── types.py
│   │   ├── meta/
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       └── filesystem.py  # Shared filesystem/system tools for hands + MCP
│   │   └── hands/v1/
│   │       ├── __init__.py
│   │       └── hand/         # Hand package (base, langgraph, atomic, iterative, e2e, cli/*)
│   ├── cli/                  # CLI entry point (depends on lib)
│   │   └── main.py
│   └── server/               # App-mode server (depends on lib)
│       ├── app.py            # FastAPI application
│       ├── celery_app.py     # Celery app + tasks
│       ├── mcp_server.py     # MCP server entry point/tools
│       └── task_result.py    # Task result normalization helpers
├── tests/                    # Test suite (pytest)
├── docs/                     # MkDocs source for API docs
├── .github/workflows/
│   ├── ci.yml                # CI: ruff, tests+coverage, multi-Python, Codecov upload
│   └── docs.yml              # Build + deploy docs to GitHub Pages
├── Dockerfile                # Multi-stage: server, worker, beat, flower
├── compose.yaml              # Full stack: server, worker, beat, flower, redis, postgres
├── .env.example              # Env var template for Compose
├── mkdocs.yml                # MkDocs + mkdocstrings config
├── obsidian/docs/            # Design notes (Obsidian vault)
├── pyproject.toml            # Project config (uv, ruff, ty, pytest)
├── .pre-commit-config.yaml   # Pre-commit hooks (ruff + ty)
├── AGENT.md                  # AI agent guidelines (self-updating)
├── TODO.md                   # Project roadmap
├── LICENSE                   # Apache 2.0
└── README.md
```

## How it works

1. **Ingest** — You provide a local repo path or GitHub `owner/repo` reference. The CLI indexes local paths directly and auto-clones `owner/repo` inputs to a temp workspace (deleted automatically on exit; configure the location with `HELPING_HANDS_REPO_TMP`).
2. **Understand** — The tool feeds repo context (file tree, key files, existing conventions) to an AI model so it can reason about the codebase.
3. **Build** — You describe the feature or change you want. The agent proposes a plan, writes the code, and presents diffs for your review.
4. **Iterate** — Accept, reject, or refine. The agent learns from your feedback and adjusts its approach.
5. **Record** — Preferences and patterns discovered during the session are captured back into `AGENT.md` so future sessions start smarter.

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

## Configuration

`helping_hands` currently reads configuration from:

1. CLI flags (highest priority)
2. Environment variables (`HELPING_HANDS_*`)
3. Built-in defaults

Environment variables are loaded from `.env` files in the current working
directory (and target repo directory when available), without overriding
already-exported shell variables.

Key settings:

| Setting | Env var | Description |
|---|---|---|
| `model` | `HELPING_HANDS_MODEL` | AI model to use; supports bare models (e.g. `gpt-5.2`) or `provider/model` (e.g. `anthropic/claude-3-5-sonnet-latest`) |
| `repo` | — | Local path or GitHub `owner/repo` target |
| `verbose` | `HELPING_HANDS_VERBOSE` | Enable detailed logging |
| `use_native_cli_auth` | `HELPING_HANDS_USE_NATIVE_CLI_AUTH` | For `codexcli`/`claudecodecli`, strip provider API key env vars so native CLI auth/session is used |
| — | `HELPING_HANDS_REPO_TMP` | Directory for temporary repo clones. Defaults to the OS temp dir (`/var/folders/…` on macOS). Set to a known path (e.g. `/tmp/helping_hands`) to keep clones out of the OS temp dir. Clones are deleted automatically after each run. |

Key CLI flags:

- `--backend {basic-langgraph,basic-atomic,basic-agent}` — run iterative basic hands
- `--backend codexcli` — run Codex CLI backend (initialize/learn repo, then execute task)
- `--backend claudecodecli` — run Claude Code CLI backend (initialize/learn repo, then execute task)
- `--backend docker-sandbox-claude` — run Claude Code inside a Docker Desktop microVM sandbox (requires Docker Desktop 4.49+, `ANTHROPIC_API_KEY`)
- `--backend goose` — run Goose CLI backend (initialize/learn repo, then execute task)
- `--backend geminicli` — run Gemini CLI backend (initialize/learn repo, then execute task)
- `--backend opencodecli` — run OpenCode CLI backend (initialize/learn repo, then execute task)
- `--backend devincli` — run Devin CLI backend (initialize/learn repo, then execute task)
- `--max-iterations N` — cap iterative hand loops
- `--no-pr` — disable final commit/push/PR side effects
- `--e2e` and `--pr-number` — run E2E flow and optionally resume existing PR
- `--use-native-cli-auth` — for `codexcli`/`claudecodecli`/`devincli`, ignore provider API key env vars and rely on local CLI auth/session

### Backend environment variables

Each backend requires different API keys and env vars depending on whether it
calls an external CLI subprocess or uses a Python AI provider SDK directly.

| Backend | Auth method | Required env vars | Notes |
|---|---|---|---|
| `e2e` | — | `GITHUB_TOKEN` | No AI model; tests clone/edit/commit/push/PR flow only |
| `basic-langgraph` | **API key** (Python SDK) | Provider-dependent (see below) | Uses `langchain` + provider SDK in-process |
| `basic-atomic` | **API key** (Python SDK) | Provider-dependent (see below) | Uses `atomic-agents` + `instructor` SDK in-process |
| `basic-agent` | **API key** (Python SDK) | Provider-dependent (see below) | Same deps as `basic-atomic` |
| `codexcli` | **Native CLI** (`codex exec`) | `OPENAI_API_KEY` | Runs `codex` as subprocess; **native CLI auth** supported via `--use-native-cli-auth` (strips `OPENAI_API_KEY` from subprocess env, uses `codex login` session instead) |
| `claudecodecli` | **Native CLI** (`claude -p`) | `ANTHROPIC_API_KEY` | Runs `claude` as subprocess; **native CLI auth** supported via `--use-native-cli-auth` (strips `ANTHROPIC_API_KEY` from subprocess env, uses `claude auth` session instead) |
| `docker-sandbox-claude` | **Docker Sandbox** (`docker sandbox exec`) | `ANTHROPIC_API_KEY` | Runs `claude` inside a Docker Desktop microVM sandbox; requires Docker Desktop 4.49+. OAuth/Keychain auth is **not** available inside the sandbox — `ANTHROPIC_API_KEY` is required. |
| `goose` | **Native CLI** (`goose run`) | Depends on `GOOSE_PROVIDER`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, or Ollama vars | Runs `goose` as subprocess; provider/model injected via `GOOSE_PROVIDER`/`GOOSE_MODEL` env vars. Also requires `GH_TOKEN` or `GITHUB_TOKEN` |
| `geminicli` | **Native CLI** (`gemini -p`) | `GEMINI_API_KEY` | Runs `gemini` as subprocess; API key is **always required** (no native-CLI-auth toggle) |
| `opencodecli` | **Native CLI** (`opencode run`) | Provider-dependent (via `opencode.json`) | Runs `opencode` as subprocess; model passed as `provider/model` (e.g. `litellm/claude-sonnet-4-6`). Configure providers in `~/.config/opencode/opencode.json`. |

**Iterative backend provider env vars** (`basic-langgraph`, `basic-atomic`, `basic-agent`):

These backends resolve the `--model` flag through the AI provider system. The
required API key depends on which provider the model maps to:

| Provider | Env var | Example `--model` values |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-5.2`, `openai/gpt-5.2` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest`, `anthropic/claude-sonnet-4-5` |
| Google | `GOOGLE_API_KEY` | `gemini-2.0-flash`, `google/gemini-2.0-flash` |
| Ollama (default) | `OLLAMA_API_KEY` (optional), `OLLAMA_BASE_URL` | `llama3.2:latest`, `ollama/llama3.2:latest`, or `default` |
| LiteLLM | (via litellm config) | `basic-atomic`/`basic-agent` only |

When `--model` is unset or `default`, all iterative backends default to **Ollama**
(`llama3.2:latest`) — no cloud API key required.

Codex CLI backend notes:

- **Env vars:** `OPENAI_API_KEY` (API key mode, default) or local `codex login` session (**native CLI auth** mode via `--use-native-cli-auth`)
- Default command: `codex exec`
- Default model passed to codex: `gpt-5.2` (unless overridden with `--model` or command override)
- Default Codex safety mode:
  - host runtime: `--sandbox workspace-write`
  - container runtime (`/.dockerenv`): `--sandbox danger-full-access` (avoids landlock failures)
  - override with `HELPING_HANDS_CODEX_SANDBOX_MODE`
- Default Codex automation mode includes `--skip-git-repo-check` (disable with `HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK=0`)
- Override command via `HELPING_HANDS_CODEX_CLI_CMD`
- Optional placeholders supported in the override string:
  - `{prompt}`
  - `{repo}`
  - `{model}`
- Optional container mode:
  - `HELPING_HANDS_CODEX_CONTAINER=1`
  - `HELPING_HANDS_CODEX_CONTAINER_IMAGE=<image-with-codex-cli>`
  - container mode bind-mounts only the target repo to `/workspace`
- Optional native auth mode:
  - `--use-native-cli-auth` (CLI/app request)
  - or `HELPING_HANDS_USE_NATIVE_CLI_AUTH=1` (env default)
  - strips `OPENAI_API_KEY` from Codex subprocess/container env

Codex backend requirements:

- `codex` CLI must be installed and available on `PATH` (`codex --version`).
- You must be authenticated in the same shell (`codex login`) or provide a valid API key for your codex setup.
- To create/push PRs at the end of a run, set `GITHUB_TOKEN` or `GH_TOKEN` in the same shell.
- Your account must have access to the requested model; if your standalone codex default is unavailable (for example `gpt-5.3-codex`), pass `--model gpt-5.2` explicitly or update `~/.codex/config.toml`.
- By default, codex commands run with host/container-aware sandbox mode (`workspace-write` on host, `danger-full-access` in containers).
- By default, codex automation uses `--skip-git-repo-check` for non-interactive worker/CLI runs.
- If you enable container mode, Docker must be installed and the image must include the `codex` executable.
- App mode supports `codexcli`, `claudecodecli`, `docker-sandbox-claude`, `goose`, `geminicli`, and `opencodecli`; ensure the worker runtime has each CLI installed/authenticated as needed.
- The included Dockerfile installs `@openai/codex` and Goose CLI in app/worker images.
- The included Dockerfile does **not** install Claude Code CLI by default.
- No extra Python optional dependency is required for `codexcli` itself (unlike `--extra langchain` and `--extra atomic` used by other iterative backends).

Codex backend smoke test:

```bash
codex exec --model gpt-5.2 "Reply with READY and one sentence."
```

CLI subprocess runtime controls (all CLI backends):

- `HELPING_HANDS_CLI_IO_POLL_SECONDS` (default: `2`) — stdout polling interval.
- `HELPING_HANDS_CLI_HEARTBEAT_SECONDS` (default: `20`) — emit a
  "still running" line (including elapsed/timeout seconds) when command output
  is quiet.
- `HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS` (default: `900`) — terminate a subprocess that produces no output
  for too long.

Claude Code backend notes:

- **Env vars:** `ANTHROPIC_API_KEY` (API key mode, default) or local `claude auth` session (**native CLI auth** mode via `--use-native-cli-auth`)
- Default command: `claude -p`
- If `claude` is missing and `npx` is available, backend auto-falls back to:
  `npx -y @anthropic-ai/claude-code -p ...`
- Default non-interactive automation flag in non-root runtimes:
  `--dangerously-skip-permissions` (disable with
  `HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS=0`)
- When Claude rejects that flag under root/sudo, the backend automatically
  retries without the flag.
- If Claude requests write approval and no edits are applied after retry, the
  run now fails with a clear runtime error instead of reporting success.
- Override command via `HELPING_HANDS_CLAUDE_CLI_CMD`
- Optional placeholders supported in the override string:
  - `{prompt}`
  - `{repo}`
  - `{model}`
- Optional container mode:
  - `HELPING_HANDS_CLAUDE_CONTAINER=1`
  - `HELPING_HANDS_CLAUDE_CONTAINER_IMAGE=<image-with-claude-cli>`
- Optional native auth mode:
  - `--use-native-cli-auth` (CLI/app request)
  - or `HELPING_HANDS_USE_NATIVE_CLI_AUTH=1` (env default)
  - strips `ANTHROPIC_API_KEY` from Claude subprocess/container env

Claude Code backend requirements:

- `claude` CLI on `PATH`, or `npx` available so fallback command can run.
- Ensure authentication is configured (typically `ANTHROPIC_API_KEY`).
- To create/push PRs at the end of a run, set `GITHUB_TOKEN` or `GH_TOKEN`.
- In Docker/app mode, if you rely on `npx` fallback, worker runtime needs
  network access to download `@anthropic-ai/claude-code`.
- The bundled Docker app/worker images run as non-root so non-interactive
  Claude permission mode can be used by default.
- If an edit-intent prompt returns only prose with no git changes, the backend
  automatically runs one extra enforcement pass to apply edits directly.

Docker Sandbox Claude backend notes:

- Runs Claude Code inside a [Docker Desktop sandbox](https://docs.docker.com/ai/sandboxes/) (microVM isolation)
- **Env vars:** `ANTHROPIC_API_KEY` (**required** — host macOS Keychain/OAuth tokens cannot be forwarded into the sandbox)
- Lifecycle: creates a sandbox with `docker sandbox create`, executes Claude via `docker sandbox exec`, cleans up with `docker sandbox rm`
- The workspace directory is automatically synced between host and sandbox at the same absolute path
- The sandbox persists across the init and task phases, so packages installed during init are available during task execution
- All `claudecodecli` features are inherited: `--output-format stream-json` parsing, `--dangerously-skip-permissions`, retry-on-no-changes
- `HELPING_HANDS_DOCKER_SANDBOX_CLEANUP` (default: `1`) — set to `0` to keep the sandbox after the run completes (useful for debugging)
- `HELPING_HANDS_DOCKER_SANDBOX_NAME` — override the auto-generated sandbox name
- `HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE` — custom base image (passed to `docker sandbox create --template`)

Docker Sandbox Claude backend requirements:

- **Docker Desktop 4.49+** with the `docker sandbox` CLI plugin (bundled with Docker Desktop)
- macOS or Windows (experimental); Linux requires Docker Desktop 4.57+ for legacy container-based sandboxes
- `ANTHROPIC_API_KEY` must be set (OAuth login uses macOS Keychain which is inaccessible from the sandbox)
- To create/push PRs at the end of a run, set `GITHUB_TOKEN` or `GH_TOKEN`

Docker Sandbox Claude backend smoke test:

```bash
ANTHROPIC_API_KEY=sk-ant-... uv run helping-hands owner/repo --backend docker-sandbox-claude --prompt "Implement one small safe improvement"
```

Goose backend notes:

- **Env vars:** Depends on `GOOSE_PROVIDER` — `OPENAI_API_KEY` (openai), `ANTHROPIC_API_KEY` (anthropic), `GOOGLE_API_KEY` (google), or `OLLAMA_HOST`/`OLLAMA_API_KEY` (ollama). Always requires `GH_TOKEN` or `GITHUB_TOKEN`.
- Default command: `goose run --with-builtin developer --text`
- Override command via `HELPING_HANDS_GOOSE_CLI_CMD`
- The backend auto-adds `--with-builtin developer` for `goose run` commands if
  missing, so local file editing tools are available.
- **Provider/model resolution priority:**
  1. `--model provider/model` (from CLI or frontend) — highest priority
  2. `GOOSE_PROVIDER` / `GOOSE_MODEL` environment variables
  3. **Goose config YAML** (`~/.config/goose/config.yaml`) — the backend reads
     `GOOSE_PROVIDER` and `GOOSE_MODEL` keys from this file automatically, so
     `goose configure` settings are respected without extra env vars
  4. Class defaults: `ollama` + `llama3.2:latest`
- Goose-native providers like `codex` are passed through as-is (no API key
  mapping needed — codex uses its own logged-in session).
- For remote Ollama instances, set `OLLAMA_HOST` (e.g.
  `http://192.168.1.143:11434`).
- Goose runs require `GH_TOKEN` or `GITHUB_TOKEN`.
- If only one of `GH_TOKEN` / `GITHUB_TOKEN` is set, runtime mirrors it to both
  variables so Goose/`gh` use token auth consistently.
- Local GitHub auth fallback is intentionally disabled for Goose runs.

Goose model examples:

```bash
# Goose with provider/model from goose config YAML (no --model needed)
uv run helping-hands owner/repo --backend goose --prompt "Implement X"

# Goose + OpenAI (provider inferred from gpt-* model)
uv run helping-hands owner/repo --backend goose --model gpt-5.2 --prompt "Implement X"

# Goose + Claude (explicit provider/model form)
uv run helping-hands owner/repo --backend goose --model anthropic/claude-sonnet-4-5 --prompt "Implement X"
```

OpenCode backend notes:

- **Model format:** `provider/model` (e.g. `litellm/claude-sonnet-4-6`). The
  provider prefix is required — OpenCode uses it to route to the correct backend.
- Default command: `opencode run`
- Override command via `HELPING_HANDS_OPENCODE_CLI_CMD`
- **Auth:** Provider-dependent. The resolved provider prefix (before `/`) is
  mapped to the standard API key env var (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  etc.). Configure providers in `~/.config/opencode/opencode.json`.
- If no model is specified, OpenCode picks its own default.
- No native-CLI-auth toggle — API keys are always forwarded.

OpenCode model examples:

```bash
# OpenCode + LiteLLM/Claude
uv run helping-hands owner/repo --backend opencodecli --model litellm/claude-sonnet-4-6 --prompt "Implement X"

# OpenCode with default model (from opencode config)
uv run helping-hands owner/repo --backend opencodecli --prompt "Implement X"
```

Gemini CLI note:

- **Env vars:** `GEMINI_API_KEY` (always required; no native-CLI-auth toggle)
- Gemini `-p` runs may be quiet before producing output; `helping-hands`
  heartbeats continue while waiting.
- `geminicli` injects `--approval-mode auto_edit` by default for
  non-interactive scripted runs (override by explicitly setting
  `--approval-mode` in `HELPING_HANDS_GEMINI_CLI_CMD`).
- Default idle timeout is now 900s for all CLI backends.
- Override with `HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS=<seconds>` when needed.
- If Gemini rejects a deprecated/unavailable model, `geminicli` retries once
  without `--model` so Gemini CLI can pick a default available model.

Devin CLI backend notes:

- **Env vars:** `DEVIN_API_KEY` (required unless using native CLI auth)
- Default command: `devin -p`
- Default permission mode: `dangerous` (auto-approves all tools for non-interactive use)
- Override with `HELPING_HANDS_DEVIN_PERMISSION_MODE=auto` to restrict to read-only auto-approval
- Override command via `HELPING_HANDS_DEVIN_CLI_CMD`
- Supports native CLI auth toggle via `HELPING_HANDS_DEVIN_USE_NATIVE_CLI_AUTH=1`
  (strips `DEVIN_API_KEY` from subprocess env so Devin uses its own session auth).

Devin CLI examples:

```bash
# Devin CLI
uv run helping-hands owner/repo --backend devincli --prompt "Implement X"

# Devin CLI with native auth (ignore DEVIN_API_KEY, use devin session)
uv run helping-hands owner/repo --backend devincli --use-native-cli-auth --prompt "Implement X"
```


Backend command examples:

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

# docker-sandbox-claude (requires Docker Desktop 4.49+ and ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY=sk-ant-... uv run helping-hands "suryarastogi/helping_hands" --backend docker-sandbox-claude --prompt "Implement one small safe improvement"

# goose
uv run helping-hands "suryarastogi/helping_hands" --backend goose --prompt "Implement one small safe improvement"

# geminicli
uv run helping-hands "suryarastogi/helping_hands" --backend geminicli --prompt "Implement one small safe improvement"

# opencodecli
uv run helping-hands "suryarastogi/helping_hands" --backend opencodecli --model litellm/claude-sonnet-4-6 --prompt "Implement one small safe improvement"

# e2e
uv run helping-hands "suryarastogi/helping_hands" --e2e --prompt "CI integration run: update PR on master"
```

## Development

```bash
# Install (includes dev deps: pytest, ruff, pre-commit)
uv sync --dev

# Install optional backend deps
uv sync --extra langchain
# or
uv sync --extra atomic

# Lint + format
uv run ruff check .
uv run ruff format --check .

# Run tests
uv run pytest -v

# Coverage report (terminal + XML)
uv run pytest -v --cov-report=term-missing --cov-report=xml

# CI uploads coverage.xml from the Python 3.12 job to Codecov
# (set CODECOV_TOKEN in repo secrets if required)
# Frontend CI uploads frontend/coverage/lcov.info as a separate Codecov flag.

# Run live E2E integration test (opt-in; requires token + repo access)
HELPING_HANDS_RUN_E2E_INTEGRATION=1 HELPING_HANDS_E2E_PR_NUMBER=1 uv run pytest -k e2e_integration -v

# CI behavior: only master + Python 3.13 performs live push/update;
# all other matrix jobs run E2E in dry-run mode.

# Set up pre-commit hooks (one-time)
uv run pre-commit install

# Frontend quality checks
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run coverage

# Build API docs locally
uv sync --extra docs --extra server
uv run mkdocs serve
```

### Compose env defaults

`compose.yaml` now sets default in-network Celery/Redis URLs for all app-mode
services if they are not set in `.env`:

- `REDIS_URL=redis://redis:6379/0`
- `CELERY_BROKER_URL=redis://redis:6379/0`
- `CELERY_RESULT_BACKEND=redis://redis:6379/1`
- `HELPING_HANDS_FLOWER_API_URL=http://flower:5555` (server-side `/tasks/current`
  discovery path)

## License

Apache 2.0 — see [LICENSE](LICENSE).
