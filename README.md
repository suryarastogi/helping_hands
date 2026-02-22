# helping_hands

**AI-powered repo builder** — point it at a codebase, describe what you want, and let an AI agent help you build and ship features.

## What is this?

`helping_hands` is a Python tool that takes a git repository as input, understands its structure and conventions, and collaborates with you to add features, fix bugs, and evolve the codebase using AI. It can run in **CLI mode** (interactive in the terminal) or **app mode** (server with background workers).

### Modes

- **CLI mode** (default) — Run `helping_hands <repo>` or `helping_hands <owner/repo>`. You can index only, or run iterative backends (`basic-langgraph`, `basic-atomic`, `basic-agent`) with streamed output.
- **App mode** — Runs a FastAPI server plus a worker stack (Celery, Redis, Postgres) so jobs run asynchronously and on a schedule (cron). Includes Flower for queue monitoring. Use when you want a persistent service, queued or scheduled repo-building tasks, or a UI.

### Execution flow

- **Server mode**: `server -> enqueue hand task -> hand executes`
- **CLI mode**: `cli -> hand executes`

For asynchronous runs, the hand UUID is the Celery task ID. For synchronous
runs, UUIDs are generated in-hand as needed.

- `E2EHand` uses `{hand_uuid}/git/{repo}` workspace layout and supports
  new PR creation plus resume/update via `--pr-number`.
- Basic iterative hands (`basic-langgraph`, `basic-atomic`) operate on the
  target repo context and, by default, attempt a final commit/push/PR step.
  Disable with `--no-pr`.
- Iterative basic hands can request file contents using `@@READ: path` and
  apply edits using `@@FILE` blocks in-model.
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
  stepwise implementation loops with live streaming, interruption, and optional
  final PR creation.

## Quick start

```bash
# Clone the repo
git clone git@github.com:suryarastogi/helping_hands.git
cd helping_hands

# Install with uv (creates .venv automatically)
uv sync --dev

# Run in CLI mode (default) against a target repo
uv run helping-hands <local-path-or-owner/repo>

# Run iterative LangGraph backend (owner/repo is auto-cloned)
uv run helping-hands owner/repo --backend basic-langgraph --model gpt-4.1-mini --prompt "Implement X" --max-iterations 4

# Disable final commit/push/PR step explicitly
uv run helping-hands owner/repo --backend basic-langgraph --model gpt-4.1-mini --prompt "Implement X" --max-iterations 4 --no-pr

# Run E2E mode against a GitHub repo (owner/repo)
uv run helping-hands owner/repo --e2e --prompt "E2E smoke test"

# Resume/update an existing PR (e.g., PR #1)
uv run helping-hands owner/repo --e2e --pr-number 1 --prompt "Update PR 1"

# App mode: start the full stack with Docker Compose
cp .env.example .env  # edit as needed
docker compose up --build
```

## Project structure

```
helping_hands/
├── src/helping_hands/        # Main package
│   ├── lib/                  # Core library (config, repo, github, hands)
│   │   ├── config.py
│   │   ├── repo.py
│   │   ├── github.py
│   │   └── hands/v1/         # Hand backends (LangGraph, Atomic, Basic iterative, E2E, CLI scaffolds)
│   ├── cli/                  # CLI entry point (depends on lib)
│   │   └── main.py
│   └── server/               # App-mode server (depends on lib)
│       ├── app.py            # FastAPI application
│       └── celery_app.py     # Celery app + tasks
├── tests/                    # Test suite (pytest)
├── docs/                     # MkDocs source for API docs
├── .github/workflows/
│   ├── ci.yml                # CI: ruff, tests, multi-Python
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
| `model` | `HELPING_HANDS_MODEL` | AI model to use (set to a real provider model, e.g. `gpt-4.1-mini`) |
| `repo` | — | Local path or GitHub `owner/repo` target |
| `verbose` | `HELPING_HANDS_VERBOSE` | Enable detailed logging |

Key CLI flags:

- `--backend {basic-langgraph,basic-atomic,basic-agent}` — run iterative basic hands
- `--max-iterations N` — cap iterative hand loops
- `--no-pr` — disable final commit/push/PR side effects
- `--e2e` and `--pr-number` — run E2E flow and optionally resume existing PR

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

## License

Apache 2.0 — see [LICENSE](LICENSE).
