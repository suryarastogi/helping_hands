# Project todos

## 1. Set up Python project under `src/helping_hands`

- [x] **Layout** — Create `src/helping_hands/` with package structure:
  - [x] `src/helping_hands/lib/` — core library (repo, agent, config; used by both CLI and server)
  - [x] `src/helping_hands/cli/` — CLI entry point and terminal UI (depends on lib only)
  - [x] `src/helping_hands/server/` — app-mode server (depends on lib only, placeholder)
  - [x] `pyproject.toml` at repo root with project name `helping-hands`, uv-compatible
- [x] **Tooling**
  - [x] **uv** — venv and dependency management (`uv sync --dev`)
  - [x] **ruff** — Lint and format, config in `pyproject.toml`
  - [x] **ty** — Type checker config in `pyproject.toml`
  - [x] **pre-commit** — `.pre-commit-config.yaml` with ruff + ty hooks
- [x] **CI/CD**
  - [x] GitHub Actions workflow (`.github/workflows/ci.yml`) on push/PR:
    - [x] Install with uv, run tests (Python 3.12, 3.13, 3.14)
    - [x] ruff check + ruff format
    - [x] Coverage reporting (`pytest-cov`) + XML upload to Codecov (Python 3.12 job)
    - [ ] Type check step (add when ty has a stable CI runner)
    - [ ] Optional: build/publish or deploy steps
- [x] **Tests**
  - [x] `tests/` layout with test files for lib and cli (suite maintained and passing in CI)
  - [x] pytest as runner, configured in `pyproject.toml`
  - [x] Coverage summary and missing lines reported by default in test runs

## 2. Dockerise app mode and add Compose

- [x] **Docker** — Multi-stage `Dockerfile` (server, worker, beat, flower targets)
- [x] **Compose** — `compose.yaml` with services:
  - [x] **Main server** — FastAPI via uvicorn
  - [x] **Workers** — Celery worker container
  - [x] **Beat** — Celery Beat for scheduled tasks
  - [x] **Redis** — Broker with health check
  - [x] **Postgres** — Database with health check
  - [x] **Flower** — Celery monitoring UI
- [x] `.env.example` with all env vars; server and workers share Redis + Postgres via Compose network

## 3. Autodocs generation and serving on GitHub

- [x] **Doc tool** — MkDocs Material + mkdocstrings; `docs/` source with API reference pages for lib, cli, server
- [x] **Build in CI** — `.github/workflows/docs.yml` builds on push to main (docs/, mkdocs.yml, src/ changes)
- [x] **Serve on GitHub** — Deploys to GitHub Pages via `actions/deploy-pages`

## 4. Hand backend scaffolding vs implementation

- [x] **Dotenv bootstrap** — `Config.from_env()` loads `.env` from cwd and repo path (without overriding exported env vars)
- [x] **E2E hand flow implemented** — `E2EHand` executes clone -> minimal edit -> commit -> push -> PR, with hand UUID and `{hand_uuid}/git/{repo}` workspace layout
- [x] **Task ID propagation** — async runs reuse Celery task ID as `hand_uuid`; sync CLI runs generate UUID inside the hand
- [x] **PR resume/update support** — optional `pr_number` updates an existing PR branch instead of opening a new PR
- [x] **Live integration coverage** — opt-in pytest integration test can run E2E hand against CI-provided GitHub token/repo
- [x] **Safe CI gating** — integration test auto-runs dry-run off `master`; only `master` performs real PR updates
  - [x] **CLI hand implementations** — `ClaudeCodeHand`, `CodexCLIHand`, `GooseCLIHand`, and `GeminiCLIHand` backends implemented under `src/helping_hands/lib/hands/v1/hand/cli/`.
  - [x] **Basic iterative hands implemented** — `BasicLangGraphHand` and `BasicAtomicHand` stream iterative progress, support interruption, and can apply inline file edits.
  - [x] **Backend selection/routing (CLI basic + E2E)** — CLI supports `--backend {basic-langgraph,basic-atomic,basic-agent}` and `--e2e`.
  - [x] **Owner/repo input in CLI** — non-E2E runs accept `owner/repo` and clone to a temporary workspace automatically.
  - [x] **Default final PR step with opt-out** — hands attempt final commit/push/PR by default; disable explicitly via `--no-pr` (and `--e2e --no-pr` maps to dry-run).
  - [x] **Non-interactive token push path** — final push config uses authenticated GitHub remote with disabled interactive credential prompts.
  - [x] **Claude CLI execution** — Subprocess-backed Claude Code flow with two phases, streaming output, `npx` fallback, `--dangerously-skip-permissions` handling, and edit-intent retry logic.
  - [x] **Codex CLI execution** — Subprocess-backed codex flow with two phases (initialize/learn repo, then task execution), streaming output, interruption support, and final PR integration.
  - [x] **Gemini CLI execution** — Subprocess-backed Gemini flow with two phases, streaming output, `--approval-mode auto_edit` default, and model-not-found retry.
  - [x] **Goose CLI execution** — Subprocess-backed Goose flow with two phases, provider/model auto-derivation, `GH_TOKEN` mirroring, and `--with-builtin developer` injection.
  - [x] **Backend selection/routing (full matrix)** — All backends routable via `--backend` in CLI and app mode: `basic-langgraph`, `basic-atomic`, `basic-agent`, `codexcli`, `claudecodecli`, `goose`, `geminicli`.
  - [x] **Streaming for CLI hands** — All CLI hands stream subprocess output incrementally with heartbeat and idle timeout support.
  - [ ] **E2E hardening** — Add branch collision handling, optional draft PR mode, and idempotency guards for reruns

---

*Update this file as items are completed. Design notes live in `obsidian/docs/`.*
