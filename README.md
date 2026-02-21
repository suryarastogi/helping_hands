# helping_hands

**AI-powered repo builder** — point it at a codebase, describe what you want, and let an AI agent help you build and ship features.

## What is this?

`helping_hands` is a Python tool that takes a git repository as input, understands its structure and conventions, and collaborates with you to add features, fix bugs, and evolve the codebase using AI. It can run in **CLI mode** (interactive in the terminal) or **app mode** (server with background workers).

### Modes

- **CLI mode** (default) — Run `helping_hands <repo>`. You work in the terminal; the hand streams responses and proposes edits. Best for local, interactive use.
- **App mode** — Runs a fast web server plus a worker stack (Celery, Redis, Postgres) so jobs run asynchronously and on a schedule (cron). Use when you want a persistent service, queued or scheduled repo-building tasks, or a UI. See the [Obsidian docs](obsidian/docs/) for the intended architecture; implementation is planned, not yet built.

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

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in CLI mode (default) against a target repo
python -m helping_hands <path-or-url-to-repo>

# App mode (when implemented): start server + workers
# python -m helping_hands serve
```

## Project structure

```
helping_hands/
├── helping_hands/       # Core package
│   ├── __init__.py
│   ├── cli.py           # CLI entry point
│   ├── repo.py          # Repo cloning, indexing, context building
│   ├── agent.py         # AI agent orchestration
│   └── config.py        # Configuration and preferences
├── tests/               # Test suite
├── obsidian/docs/       # Design notes (Obsidian vault)
├── AGENT.md             # AI agent guidelines (self-updating)
├── requirements.txt     # Python dependencies
├── LICENSE              # Apache 2.0
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
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Lint
ruff check .
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
