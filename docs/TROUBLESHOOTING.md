# Troubleshooting

Common issues and solutions when using helping_hands. Run
`helping-hands doctor` first — it checks most prerequisites automatically.

---

## Environment setup

### Python version too old

**Symptom:** `helping-hands doctor` reports "requires 3.12+" or import errors
on startup.

**Fix:** Install Python 3.12 or later. With `pyenv`:

```bash
pyenv install 3.14
pyenv local 3.14
uv sync --dev
```

### git not found

**Symptom:** `helping-hands doctor` reports "git not found" or clone operations
fail with `FileNotFoundError`.

**Fix:** Install git via your package manager:

```bash
# macOS
brew install git

# Ubuntu / Debian
sudo apt install git
```

### uv not found

**Symptom:** `helping-hands doctor` warns "uv not found".

**Fix:** Install uv (recommended for dependency management):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## API keys

### No AI provider key found

**Symptom:** `helping-hands doctor` reports "no AI provider key found" or
the hand exits immediately with a model resolution error.

**Fix:** Set at least one provider API key:

```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
# or
export GOOGLE_API_KEY="AIza..."
```

Add these to your shell profile (`~/.bashrc`, `~/.zshrc`) or a `.env` file
in the repo root.

### GitHub token not set

**Symptom:** PR creation fails with authentication errors, or
`helping-hands doctor` warns "no GitHub token".

**Fix:** Set `GITHUB_TOKEN` or `GH_TOKEN`:

```bash
export GITHUB_TOKEN="ghp_..."
```

Generate a token at <https://github.com/settings/tokens> with `repo` scope.
Use `--no-pr` to skip PR creation when evaluating locally.

---

## Backend-specific issues

### CLI tool not found (claude, codex, goose, gemini)

**Symptom:** `Error: claude: command not found` (or similar for other backends).

**Fix:** Install the required CLI tool and ensure it is on your PATH:

- **Claude Code:** `npm install -g @anthropic-ai/claude-code`
- **Codex:** `npm install -g @openai/codex`
- **Goose:** See <https://github.com/block/goose>
- **Gemini:** `npm install -g @anthropic-ai/gemini-cli` (or install via pip)

Check with `which claude` (or the relevant binary name).

### Docker not found (docker-sandbox backends)

**Symptom:** `helping-hands doctor` warns "docker not found" or the
`docker-sandbox-claude` backend fails to start.

**Fix:** Install Docker Desktop (<https://docs.docker.com/get-docker/>)
and ensure the `docker` CLI and the `docker sandbox` plugin are available:

```bash
docker --version
docker sandbox --help
```

### Optional extras not installed

**Symptom:** `ImportError` for `langchain_core`, `atomic_agents`, or
`fastapi` when using the corresponding backend or server mode.

**Fix:** Install the required extra:

```bash
uv sync --extra langchain   # for basic-langgraph backend
uv sync --extra atomic      # for basic-atomic backend
uv sync --extra server      # for FastAPI server + Celery workers
```

---

## Common runtime errors

### Idle timeout — CLI hand terminated

**Symptom:** `<backend> produced no output for Xs and was terminated.`

**Cause:** The CLI subprocess produced no stdout/stderr for longer than the
idle timeout (default: 300 seconds).

**Fix:** Increase the timeout:

```bash
export HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS=600
```

Or check that the underlying CLI tool is not stuck waiting for interactive
input (e.g. a permission prompt in Claude Code).

### Model not found / provider error

**Symptom:** `ValueError: cannot resolve model "..."` or API error from the
provider.

**Fix:**
- Verify the model string is correct (e.g. `gpt-4o`, `claude-sonnet-4-5`,
  `gemini-2.5-pro`).
- Use `provider/model` format to force a specific provider
  (e.g. `anthropic/claude-sonnet-4-5`).
- Check that the corresponding API key is set.

### Permission denied during git push

**Symptom:** `fatal: could not read Username for 'https://github.com'`

**Cause:** The `GITHUB_TOKEN` is missing or expired, so git falls back to
interactive authentication which fails in non-interactive mode.

**Fix:** Set a valid `GITHUB_TOKEN` with `repo` scope. helping_hands uses
token-authenticated HTTPS remotes to avoid interactive prompts.

---

## Server mode

### Redis connection refused

**Symptom:** `ConnectionError: Error connecting to Redis` when starting the
server or Celery workers.

**Fix:** Start Redis (default port 6379):

```bash
# Via Docker
docker run -d -p 6379:6379 redis:7

# Or via local-stack script
./scripts/run-local-stack.sh start
```

Check with `redis-cli ping` — it should respond `PONG`.

### docker compose not available

**Symptom:** `helping-hands doctor` warns "docker compose subcommand not
available" or `docker compose up` fails.

**Fix:** Update Docker Desktop to a version that includes `docker compose`
(v2). The standalone `docker-compose` binary (v1) is deprecated.

```bash
docker compose version
```

---

## Getting more help

- Run `helping-hands doctor` for a full environment check.
- Check `examples/fix-greeting/` for a minimal working example.
- File issues at <https://github.com/anthropics/helping-hands/issues>.
