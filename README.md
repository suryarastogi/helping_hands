# helping_hands

**AI-powered repo builder** — point it at a codebase, describe what you want, and let an AI agent help you build and ship features.

## What is this?

`helping_hands` is a Python tool that takes a git repository as input, understands its structure and conventions, and collaborates with you to add features, fix bugs, and evolve the codebase using AI. It can run in **CLI mode** (interactive in the terminal) or **app mode** (server with background workers).

### Modes

- **CLI mode** (default) — Run `helping_hands <repo>`. You work in the terminal; the hand streams responses and proposes edits. Best for local, interactive use.
- **App mode** — Runs a FastAPI server plus a worker stack (Celery, Redis, Postgres) so jobs run asynchronously and on a schedule (cron). Includes Flower for queue monitoring. Use when you want a persistent service, queued or scheduled repo-building tasks, or a UI.

### Key ideas

- **Repo-aware**: Clones or reads a local repo, indexes the file tree, and builds context so the AI understands what it's working with.
- **Conversational building**: Describe what you want in plain language. The agent proposes changes, writes code, and iterates with you.
- **Convention-respectful**: Learns the repo's patterns (naming, structure, style) and follows them in generated code.
- **Self-improving guidance**: Ships with an `AGENT.md` file that the agent updates over time as it learns your preferences for tone, style, and design.

## Quick start

```bash
# Clone the repo
git clone git@github.com:suryarastogi/helping_hands.git
cd helping_hands

# Install with uv (creates .venv automatically)
uv sync --dev

# Run in CLI mode (default) against a target repo
uv run helping-hands <path-or-url-to-repo>

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
│   │   └── hands/v1/         # Hand backends (LangGraph, Atomic)
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
├── .pre-commit-config.yaml   # Pre-commit hooks (ruff)
├── AGENT.md                  # AI agent guidelines (self-updating)
├── TODO.md                   # Project roadmap
├── LICENSE                   # Apache 2.0
└── README.md
```

## How it works

1. **Ingest** — You provide a git repo (local path or remote URL). `helping_hands` clones it (if remote), walks the file tree, and builds a structural map.
2. **Understand** — The tool feeds repo context (file tree, key files, existing conventions) to an AI model so it can reason about the codebase.
3. **Build** — You describe the feature or change you want. The agent proposes a plan, writes the code, and presents diffs for your review.
4. **Iterate** — Accept, reject, or refine. The agent learns from your feedback and adjusts its approach.
5. **Record** — Preferences and patterns discovered during the session are captured back into `AGENT.md` so future sessions start smarter.

## Configuration

`helping_hands` reads configuration from (in priority order):

1. CLI flags
2. Environment variables (`HELPING_HANDS_*`)
3. A `.helping_hands.toml` file in the target repo or home directory

Key settings:

| Setting | Env var | Description |
|---|---|---|
| `model` | `HELPING_HANDS_MODEL` | AI model to use (default: configurable) |
| `repo` | — | Path or URL of the target repository |
| `verbose` | `HELPING_HANDS_VERBOSE` | Enable detailed logging |

## Development

```bash
# Install (includes dev deps: pytest, ruff, pre-commit)
uv sync --dev

# Lint + format
uv run ruff check .
uv run ruff format --check .

# Run tests
uv run pytest -v

# Set up pre-commit hooks (one-time)
uv run pre-commit install

# Build API docs locally
uv sync --extra docs --extra server
uv run mkdocs serve
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
