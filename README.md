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

- **CLI mode** (default) — Run `helping-hands <repo>` (local path or `owner/repo`). Supports iterative backends (`basic-langgraph`, `basic-atomic`, `basic-agent`) and external CLI backends (`codexcli`, `claudecodecli`, `docker-sandbox-claude`, `goose`, `geminicli`, `opencodecli`, `devincli`). See [docs/backends.md](docs/backends.md) for details.
- **App mode** — Runs a FastAPI server plus a worker stack (Celery, Redis, Postgres) so jobs run asynchronously and on a schedule. Includes Flower for queue monitoring and a React UI. See [docs/app-mode.md](docs/app-mode.md) for setup.

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

## How it works

1. **Ingest** — You provide a local repo path or GitHub `owner/repo` reference. The CLI indexes local paths directly and auto-clones `owner/repo` inputs to a temp workspace (deleted automatically on exit; configure the location with `HELPING_HANDS_REPO_TMP`).
2. **Understand** — The tool feeds repo context (file tree, key files, existing conventions) to an AI model so it can reason about the codebase.
3. **Build** — You describe the feature or change you want. The agent proposes a plan, writes the code, and presents diffs for your review.
4. **Iterate** — Accept, reject, or refine. The agent learns from your feedback and adjusts its approach.
5. **Record** — Preferences and patterns discovered during the session are captured back into `AGENT.md` so future sessions start smarter.

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

## Documentation

- **[Backend Reference](docs/backends.md)** — Environment variables, auth requirements, and usage notes for every backend
- **[App Mode & Scheduling](docs/app-mode.md)** — Server setup, Docker Compose, local Celery, scheduling builds
- **[Development & Contributing](docs/development.md)** — Install, lint, test, configuration reference

## License

Apache 2.0 — see [LICENSE](LICENSE).
