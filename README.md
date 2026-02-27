<p align="center">
  <img src="media/banner.png" alt="helping_hands" />
</p>

<p align="center">
  <a href="https://codecov.io/gh/suryarastogi/helping_hands">
    <img src="https://codecov.io/gh/suryarastogi/helping_hands/graph/badge.svg" alt="Coverage" />
  </a>
</p>

---

**Last updated:** February 27, 2026

## What is this?

`helping_hands` is a Python tool that takes a git repository as input, understands its structure and conventions, and collaborates with you to add features, fix bugs, and evolve the codebase using AI. It can run in **CLI mode** (interactive in the terminal) or **app mode** (server with background workers).

### Modes

- **CLI mode** (default) — Run `helping-hands <repo>` (local path) or `helping-hands <owner/repo>` (auto-clones to a temp workspace, cleaned up on exit). You can index only, or run iterative backends plus external-CLI backends with streamed output:
  - iterative: `basic-langgraph` (requires `--extra langchain`), `basic-atomic` / `basic-agent` (require `--extra atomic`)
  - external CLI: `codexcli`, `claudecodecli`, `goose`, `geminicli`
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

```bash
# Requires Python 3.12+

# Clone the repo
git clone git@github.com:suryarastogi/helping_hands.git
cd helping_hands

# Install with uv (creates .venv automatically)
uv sync --dev

# Run in CLI mode (default) against a target repo
uv run helping-hands <local-path-or-owner/repo>

# Run iterative LangGraph backend (owner/repo is auto-cloned)
uv run helping-hands owner/repo --backend basic-langgraph --model gpt-5.2 --prompt "Implement X" --max-iterations 4

# Run iterative Atomic backend
uv run helping-hands owner/repo --backend basic-atomic --model gpt-5.2 --prompt "Implement X" --max-iterations 4

# Run iterative Agent backend (same dependency extra as basic-atomic)
uv run helping-hands owner/repo --backend basic-agent --model gpt-5.2 --prompt "Implement X" --max-iterations 4

# Run Codex CLI backend (two-phase: initialize repo context, then execute task)
uv run helping-hands owner/repo --backend codexcli --model gpt-5.2 --prompt "Implement X"

# Run Claude Code CLI backend (two-phase: initialize repo context, then execute task)
uv run helping-hands owner/repo --backend claudecodecli --model anthropic/claude-sonnet-4-5 --prompt "Implement X"

# Run Gemini CLI backend (two-phase: initialize repo context, then execute task)
uv run helping-hands owner/repo --backend geminicli --prompt "Implement X"

# Force native Codex/Claude auth session usage (ignore provider API key env vars)
uv run helping-hands owner/repo --backend codexcli --model gpt-5.2 --use-native-cli-auth --prompt "Implement X"

# Run Goose CLI backend (two-phase: initialize repo context, then execute task)
uv run helping-hands owner/repo --backend goose --prompt "Implement X"

# Disable final commit/push/PR step explicitly
uv run helping-hands owner/repo --backend basic-langgraph --model gpt-5.2 --prompt "Implement X" --max-iterations 4 --no-pr

# Enable execution/web tools for iterative backends (disabled by default)
uv run helping-hands owner/repo --backend basic-langgraph --enable-execution --enable-web --prompt "Run the smoke test prompt"

# Run E2E mode against a GitHub repo (owner/repo)
uv run helping-hands owner/repo --e2e --prompt "E2E smoke test"

# Resume/update an existing PR (e.g., PR #1)
uv run helping-hands owner/repo --e2e --pr-number 1 --prompt "Update PR 1"

# App mode: start the full stack with Docker Compose
cp .env.example .env  # edit as needed
docker compose down
docker compose up --build

# Optional: run React frontend wrapper for submit/monitor flows
cd frontend
npm install
npm run dev
```

### Trigger a run in app mode

App mode enqueues Celery tasks through the FastAPI server and supports `e2e`,
iterative/basic backends, and CLI backends (`codexcli`, `claudecodecli`,
`goose`, `geminicli`).

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
- backend selection (`e2e`, `basic-langgraph`, `basic-atomic`, `basic-agent`, `codexcli`, `claudecodecli`, `goose`, `geminicli`)
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
- `--backend goose` — run Goose CLI backend (initialize/learn repo, then execute task)
- `--backend geminicli` — run Gemini CLI backend (initialize/learn repo, then execute task)
- `--max-iterations N` — cap iterative hand loops
- `--no-pr` — disable final commit/push/PR side effects
- `--e2e` and `--pr-number` — run E2E flow and optionally resume existing PR
- `--use-native-cli-auth` — for `codexcli`/`claudecodecli`, ignore provider API key env vars and rely on local CLI auth/session

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
| `goose` | **Native CLI** (`goose run`) | Depends on `GOOSE_PROVIDER`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, or Ollama vars | Runs `goose` as subprocess; provider/model injected via `GOOSE_PROVIDER`/`GOOSE_MODEL` env vars. Also requires `GH_TOKEN` or `GITHUB_TOKEN` |
| `geminicli` | **Native CLI** (`gemini -p`) | `GEMINI_API_KEY` | Runs `gemini` as subprocess; API key is **always required** (no native-CLI-auth toggle) |

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
- App mode supports `codexcli`, `claudecodecli`, `goose`, and `geminicli`; ensure the worker runtime has each CLI installed/authenticated as needed.
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

Goose backend notes:

- **Env vars:** Depends on `GOOSE_PROVIDER` — `OPENAI_API_KEY` (openai), `ANTHROPIC_API_KEY` (anthropic), `GOOGLE_API_KEY` (google), or `OLLAMA_HOST`/`OLLAMA_API_KEY` (ollama, default). Always requires `GH_TOKEN` or `GITHUB_TOKEN`.
- Default command: `goose run --with-builtin developer --text`
- Override command via `HELPING_HANDS_GOOSE_CLI_CMD`
- The backend auto-adds `--with-builtin developer` for `goose run` commands if
  missing, so local file editing tools are available.
- Provider/model are auto-injected for automation:
  - `GOOSE_PROVIDER` and `GOOSE_MODEL` are derived from `HELPING_HANDS_MODEL`
    (or default to `ollama` + `llama3.2:latest`).
- For remote Ollama instances, set `OLLAMA_HOST` (e.g.
  `http://192.168.1.143:11434`).
- Interactive `goose configure` is not required for helping_hands runs.
- Goose runs require `GH_TOKEN` or `GITHUB_TOKEN`.
- If only one of `GH_TOKEN` / `GITHUB_TOKEN` is set, runtime mirrors it to both
  variables so Goose/`gh` use token auth consistently.
- Local GitHub auth fallback is intentionally disabled for Goose runs.

Goose model examples:

```bash
# Goose + OpenAI (provider inferred from gpt-* model)
uv run helping-hands owner/repo --backend goose --model gpt-5.2 --prompt "Implement X"

# Goose + Claude (explicit provider/model form)
uv run helping-hands owner/repo --backend goose --model anthropic/claude-sonnet-4-5 --prompt "Implement X"
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

# goose
uv run helping-hands "suryarastogi/helping_hands" --backend goose --prompt "Implement one small safe improvement"

# geminicli
uv run helping-hands "suryarastogi/helping_hands" --backend geminicli --prompt "Implement one small safe improvement"

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
