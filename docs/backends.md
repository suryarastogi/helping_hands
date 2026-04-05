# Backend Reference

This page covers environment variables, auth requirements, and usage notes for every `helping_hands` backend.

## Backend environment variables

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

## Iterative backend provider env vars

`basic-langgraph`, `basic-atomic`, and `basic-agent` resolve the `--model` flag through the AI provider system. The
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

## Codex CLI

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

### Codex requirements

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

### Codex smoke test

```bash
codex exec --model gpt-5.2 "Reply with READY and one sentence."
```

## Claude Code CLI

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

### Claude Code requirements

- `claude` CLI on `PATH`, or `npx` available so fallback command can run.
- Ensure authentication is configured (typically `ANTHROPIC_API_KEY`).
- To create/push PRs at the end of a run, set `GITHUB_TOKEN` or `GH_TOKEN`.
- In Docker/app mode, if you rely on `npx` fallback, worker runtime needs
  network access to download `@anthropic-ai/claude-code`.
- The bundled Docker app/worker images run as non-root so non-interactive
  Claude permission mode can be used by default.
- If an edit-intent prompt returns only prose with no git changes, the backend
  automatically runs one extra enforcement pass to apply edits directly.

## Docker Sandbox Claude

- Runs Claude Code inside a [Docker Desktop sandbox](https://docs.docker.com/ai/sandboxes/) (microVM isolation)
- **Env vars:** `ANTHROPIC_API_KEY` (**required** — host macOS Keychain/OAuth tokens cannot be forwarded into the sandbox)
- Lifecycle: creates a sandbox with `docker sandbox create`, executes Claude via `docker sandbox exec`, cleans up with `docker sandbox rm`
- The workspace directory is automatically synced between host and sandbox at the same absolute path
- The sandbox persists across the init and task phases, so packages installed during init are available during task execution
- All `claudecodecli` features are inherited: `--output-format stream-json` parsing, `--dangerously-skip-permissions`, retry-on-no-changes
- `HELPING_HANDS_DOCKER_SANDBOX_CLEANUP` (default: `1`) — set to `0` to keep the sandbox after the run completes (useful for debugging)
- `HELPING_HANDS_DOCKER_SANDBOX_NAME` — override the auto-generated sandbox name
- `HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE` — custom base image (passed to `docker sandbox create --template`)

### Docker Sandbox requirements

- **Docker Desktop 4.49+** with the `docker sandbox` CLI plugin (bundled with Docker Desktop)
- macOS or Windows (experimental); Linux requires Docker Desktop 4.57+ for legacy container-based sandboxes
- `ANTHROPIC_API_KEY` must be set (OAuth login uses macOS Keychain which is inaccessible from the sandbox)
- To create/push PRs at the end of a run, set `GITHUB_TOKEN` or `GH_TOKEN`

### Docker Sandbox smoke test

```bash
ANTHROPIC_API_KEY=sk-ant-... uv run helping-hands owner/repo --backend docker-sandbox-claude --prompt "Implement one small safe improvement"
```

## Goose

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

### Goose model examples

```bash
# Goose with provider/model from goose config YAML (no --model needed)
uv run helping-hands owner/repo --backend goose --prompt "Implement X"

# Goose + OpenAI (provider inferred from gpt-* model)
uv run helping-hands owner/repo --backend goose --model gpt-5.2 --prompt "Implement X"

# Goose + Claude (explicit provider/model form)
uv run helping-hands owner/repo --backend goose --model anthropic/claude-sonnet-4-5 --prompt "Implement X"
```

## Gemini CLI

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

## OpenCode CLI

- **Model format:** `provider/model` (e.g. `litellm/claude-sonnet-4-6`). The
  provider prefix is required — OpenCode uses it to route to the correct backend.
- Default command: `opencode run`
- Override command via `HELPING_HANDS_OPENCODE_CLI_CMD`
- **Auth:** Provider-dependent. The resolved provider prefix (before `/`) is
  mapped to the standard API key env var (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  etc.). Configure providers in `~/.config/opencode/opencode.json`.
- If no model is specified, OpenCode picks its own default.
- No native-CLI-auth toggle — API keys are always forwarded.

### OpenCode model examples

```bash
# OpenCode + LiteLLM/Claude
uv run helping-hands owner/repo --backend opencodecli --model litellm/claude-sonnet-4-6 --prompt "Implement X"

# OpenCode with default model (from opencode config)
uv run helping-hands owner/repo --backend opencodecli --prompt "Implement X"
```

## Devin CLI

- **Env vars:** `DEVIN_API_KEY` (required unless using native CLI auth)
- Default command: `devin -p`
- Default permission mode: `dangerous` (auto-approves all tools for non-interactive use)
- Override with `HELPING_HANDS_DEVIN_PERMISSION_MODE=auto` to restrict to read-only auto-approval
- Override command via `HELPING_HANDS_DEVIN_CLI_CMD`
- Supports native CLI auth toggle via `HELPING_HANDS_DEVIN_USE_NATIVE_CLI_AUTH=1`
  (strips `DEVIN_API_KEY` from subprocess env so Devin uses its own session auth).

### Devin CLI examples

```bash
# Devin CLI
uv run helping-hands owner/repo --backend devincli --prompt "Implement X"

# Devin CLI with native auth (ignore DEVIN_API_KEY, use devin session)
uv run helping-hands owner/repo --backend devincli --use-native-cli-auth --prompt "Implement X"
```

## CLI subprocess runtime controls

These settings apply to all CLI backends (`codexcli`, `claudecodecli`, `docker-sandbox-claude`, `goose`, `geminicli`, `opencodecli`, `devincli`):

- `HELPING_HANDS_CLI_IO_POLL_SECONDS` (default: `2`) — stdout polling interval.
- `HELPING_HANDS_CLI_HEARTBEAT_SECONDS` (default: `20`) — emit a
  "still running" line (including elapsed/timeout seconds) when command output
  is quiet.
- `HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS` (default: `900`) — terminate a subprocess that produces no output
  for too long.

## Backend command examples

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

## More examples

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
