# Development & Contributing

## Setup

```bash
# Install (includes dev deps: pytest, ruff, pre-commit)
uv sync --dev

# Install optional backend deps
uv sync --extra langchain
# or
uv sync --extra atomic
```

## Lint & format

```bash
uv run ruff check .
uv run ruff format --check .
```

## Tests

```bash
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
```

## Pre-commit hooks

```bash
# Set up pre-commit hooks (one-time)
uv run pre-commit install
```

## Frontend quality checks

```bash
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run coverage
```

## API docs

```bash
# Build API docs locally
uv sync --extra docs --extra server
uv run mkdocs serve
```

## Configuration

`helping_hands` currently reads configuration from:

1. CLI flags (highest priority)
2. Environment variables (`HELPING_HANDS_*`)
3. Built-in defaults

Environment variables are loaded from `.env` files in the current working
directory (and target repo directory when available), without overriding
already-exported shell variables.

### Key settings

| Setting | Env var | Description |
|---|---|---|
| `model` | `HELPING_HANDS_MODEL` | AI model to use; supports bare models (e.g. `gpt-5.2`) or `provider/model` (e.g. `anthropic/claude-3-5-sonnet-latest`) |
| `repo` | — | Local path or GitHub `owner/repo` target |
| `verbose` | `HELPING_HANDS_VERBOSE` | Enable detailed logging |
| `use_native_cli_auth` | `HELPING_HANDS_USE_NATIVE_CLI_AUTH` | For `codexcli`/`claudecodecli`, strip provider API key env vars so native CLI auth/session is used |
| — | `HELPING_HANDS_REPO_TMP` | Directory for temporary repo clones. Defaults to the OS temp dir (`/var/folders/…` on macOS). Set to a known path (e.g. `/tmp/helping_hands`) to keep clones out of the OS temp dir. Clones are deleted automatically after each run. |

### Key CLI flags

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
