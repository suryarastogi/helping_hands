<p align="center">
  <img src="media/banner.png" alt="helping_hands" />
</p>

<p align="center">
  <a href="https://codecov.io/gh/suryarastogi/helping_hands">
    <img src="https://codecov.io/gh/suryarastogi/helping_hands/graph/badge.svg" alt="Coverage" />
  </a>
</p>

---

## What is this?

`helping_hands` is a Python tool that takes a git repository as input, understands its structure and conventions, and collaborates with you to add features, fix bugs, and evolve the codebase using AI. It can run in **CLI mode** (interactive in the terminal) or **app mode** (server with background workers).

### Modes

- **CLI mode** (default) — Run `helping_hands <repo>` or `helping_hands <owner/repo>`. You can index only, or run iterative backends (`basic-langgraph`, `basic-atomic`, `basic-agent`) with streamed output.
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
  `lib/ai_providers/` (`openai`, `anthropic`, `google`, `litellm`).
- Hands resolve model strings through provider wrappers (including
  `provider/model` forms) before adapting to backend-specific model clients.
- Push uses token-authenticated GitHub remote configuration and disables
  interactive credential prompts.

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

# Disable final commit/push/PR step explicitly
uv run helping-hands owner/repo --backend basic-langgraph --model gpt-5.2 --prompt "Implement X" --max-iterations 4 --no-pr

# Run E2E mode against a GitHub repo (owner/repo)
uv run helping-hands owner/repo --e2e --prompt "E2E smoke test"

# Resume/update an existing PR (e.g., PR #1)
uv run helping-hands owner/repo --e2e --pr-number 1 --prompt "Update PR 1"

# App mode: start the full stack with Docker Compose
cp .env.example .env  # edit as needed
docker compose up --build
```

### Trigger a run in app mode

App mode enqueues Celery tasks through the FastAPI server and supports both
`e2e` and iterative basic backends.

The built-in UI at `http://localhost:8000/` supports:
- backend selection (`e2e`, `basic-langgraph`, `basic-atomic`, `basic-agent`)
- model override
- max iterations
- optional PR number
- `no_pr` toggle
- JS polling monitor via `/tasks/{task_id}`
- no-JS fallback monitor via `/monitor/{task_id}` (auto-refresh)

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
```

Optional one-liner (requires `jq`) to enqueue and poll:

```bash
TASK_ID=$(curl -sS -X POST "http://localhost:8000/build" -H "Content-Type: application/json" -d '{"repo_path":"suryarastogi/helping_hands","prompt":"CI integration run: update PR on master"}' | jq -r .task_id); while true; do curl -sS "http://localhost:8000/tasks/$TASK_ID"; echo; sleep 2; done
```

If UI submit appears to enqueue but you do not see repeated `/tasks/<id>` requests
in logs (common when browser JS is blocked), use `/monitor/<id>`; that endpoint
refreshes server-side without client-side JavaScript.

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
│   │   │   └── types.py
│   │   ├── meta/
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       └── filesystem.py  # Shared filesystem/system tools for hands + MCP
│   │   └── hands/v1/
│   │       ├── __init__.py
│   │       └── hand/         # Hand package (base, langgraph, atomic, iterative, e2e, placeholders)
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

1. **Ingest** — You provide a local repo path or GitHub `owner/repo` reference. The CLI indexes local paths directly and auto-clones `owner/repo` inputs to a temp workspace.
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

Key CLI flags:

- `--backend {basic-langgraph,basic-atomic,basic-agent}` — run iterative basic hands
- `--max-iterations N` — cap iterative hand loops
- `--no-pr` — disable final commit/push/PR side effects
- `--e2e` and `--pr-number` — run E2E flow and optionally resume existing PR

Backend command examples:

```bash
# basic-langgraph
uv run helping-hands "suryarastogi/helping_hands" --backend basic-langgraph --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# basic-atomic
uv run helping-hands "suryarastogi/helping_hands" --backend basic-atomic --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

# basic-agent
uv run helping-hands "suryarastogi/helping_hands" --backend basic-agent --model gpt-5.2 --prompt "Implement one small safe improvement; if editing files use @@FILE blocks and end with SATISFIED: yes/no." --max-iterations 4

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

# Run live E2E integration test (opt-in; requires token + repo access)
HELPING_HANDS_RUN_E2E_INTEGRATION=1 HELPING_HANDS_E2E_PR_NUMBER=1 uv run pytest -k e2e_integration -v

# CI behavior: only master + Python 3.13 performs live push/update;
# all other matrix jobs run E2E in dry-run mode.

# Set up pre-commit hooks (one-time)
uv run pre-commit install

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

## License

Apache 2.0 — see [LICENSE](LICENSE).
