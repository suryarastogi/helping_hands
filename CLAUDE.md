# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install (Python 3.12+, uses uv)
uv sync --dev
uv sync --extra langchain --extra atomic --extra server --extra github --extra mcp

# Run CLI
uv run helping-hands <local-path-or-owner/repo> --backend basic-langgraph --model gpt-5.2 --prompt "task"

# Run MCP server
uv run helping-hands-mcp              # stdio mode
uv run helping-hands-mcp --http       # HTTP mode

# Lint & format
uv run ruff check .                   # lint
uv run ruff check --fix .             # lint with autofix
uv run ruff format --check .          # format check
uv run ruff format .                  # format

# Type check
uv run ty check src --ignore unresolved-import --ignore invalid-method-override --ignore unused-type-ignore-comment --ignore invalid-assignment --ignore call-non-callable --ignore unresolved-attribute

# Tests
uv run pytest -v                      # all tests with coverage
uv run pytest tests/test_config.py -v # single test file
uv run pytest -k test_name -v         # single test by name

# Pre-commit hooks
uv run pre-commit install
uv run pre-commit run --all-files

# Frontend (from repo root)
npm --prefix frontend install
npm --prefix frontend run dev         # dev server
npm --prefix frontend run build
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test

# App mode (Docker)
docker compose up --build
# Or local stack (data services in Docker, app processes local):
./scripts/run-local-stack.sh start
```

## Architecture

**`helping_hands` is an AI-powered repo builder** — point it at a codebase and it uses AI to add features, fix bugs, and evolve code. Runs as CLI, FastAPI server (with Celery workers), or MCP server.

### Core abstraction: Hands

Everything flows through the **Hand** base class (`src/helping_hands/lib/hands/v1/hand/base.py`). Hands are the execution backends — each one implements `run()`/`stream()` and represents a different approach to AI-driven code changes:

- **E2EHand** (`e2e.py`) — clone/edit/commit/push/PR flow for integration testing
- **IterativeHand** (`iterative.py`) — base for loop-based hands with `@@READ`/`@@FILE` in-model file operations
- **BasicLangGraphHand** (`langgraph.py`) — LangGraph agent loop (requires `--extra langchain`)
- **BasicAtomicHand** (`atomic.py`) — Atomic Agents loop (requires `--extra atomic`)
- **CLI Hands** (`cli/`) — subprocess wrappers around external CLIs: `codex.py`, `claude.py`, `goose.py`, `gemini.py`, `devin.py`

Finalization (commit/push/PR) is centralized in the base `Hand` class. All hands attempt it by default; disable with `--no-pr`.

### Provider abstraction

AI providers live in `src/helping_hands/lib/ai_providers/` with a common `AIProvider` interface. Models are specified as bare strings (`gpt-5.2`) or `provider/model` format (`anthropic/claude-sonnet-4-5`). Resolution happens in `model_provider.py`.

### Module boundaries

- `src/helping_hands/lib/` — core library (config, repo indexing, GitHub API, hands, meta tools, AI providers)
- `src/helping_hands/cli/` — CLI entry point, depends on lib
- `src/helping_hands/server/` — FastAPI app + Celery tasks + MCP server, depends on lib
- `frontend/` — React + TypeScript + Vite UI
- `tests/` — pytest suite

These layers communicate through plain data (dicts, dataclasses), not by importing each other's internals.

### System tool isolation

All filesystem/command operations for hands route through `src/helping_hands/lib/meta/tools/filesystem.py` for path-safe behavior (prevents path traversal via `resolve_repo_target()`). MCP tools use the same layer.

### Grill Me (interactive planning)

An optional feature (`GRILL_ME_ENABLED=1`) that lets users stress-test a plan before submitting a task. The frontend opens an overlay chat where the AI interviews the user about their design. Supports two backends: **Claude Code CLI** (default, read-only mode) and **Codex CLI** (stateless, full conversation embedded per turn).

- **Backend**: `src/helping_hands/server/grill.py` — long-running Celery task. Claude uses `claude -p --session-id/--resume` for multi-turn conversation; Codex uses `codex exec` with full history embedded. Redis queues for user-worker message passing.
- **Frontend**: `GrillMeOverlay` component + `useGrillSession` hook — 3-phase UI (form -> chat -> plan), polls `GET /grill/{id}` for messages.
- **Endpoints**: `POST /grill`, `POST /grill/{id}/message`, `GET /grill/{id}` — all gated by `GRILL_ME_ENABLED`.
- **Plan submission**: final plan auto-populates the submission form prompt (with `## FINAL PLAN` header stripped) and submits via `submitBuild()`.

### Multiplayer Grill Me (collaborative planning)

A parallel feature to solo Grill Me — same `GRILL_ME_ENABLED=1` flag, different code path. Activated via a campfire sprite in Hand World; opens a lobby of concurrent sessions, each discoverable and joinable by any user. Transcript, vote tally, and the pending-message batch live in a Yjs room (`mgrill-{session_id}`) and sync to all participants with sub-100ms latency; Redis holds authoritative state (status, creator, turn count) and the worker's user-message FIFO.

- **Worker**: `src/helping_hands/server/multiplayer_grill.py` — Celery task that reuses solo Grill Me's Claude/Codex CLI invocation helpers. AI-produced messages are `LPUSH`ed to the shared Redis queue `mgrill:ai_outbox`.
- **Bridge**: `src/helping_hands/server/mgrill_bridge.py` — in-process asyncio task started in FastAPI's lifespan that drains `mgrill:ai_outbox` and appends each envelope to the matching Yjs room's `messages` Y.Array. Exists because `pycrdt` 0.12 has no Python Yjs client, so the worker can't speak Yjs directly. Coordination uses a **Redis leader lock** (`mgrill:bridge:leader`, 5 s TTL, 2 s renewal) so only one bridge drains the outbox at a time — critical when multiple FastAPI processes run (eg. `--workers N`, `--reload`, or leftover zombies). Standby peers sleep without reading the outbox; a crashed leader's lock lapses within 5 s and a peer takes over.
- **REST**: all `/mgrill/*` endpoints are async and mutate the Y.Doc in-process for pending/votes/transcript side-effects.
- **Frontend**: `MultiplayerGrillOverlay` → lobby or room; `useMultiplayerGrill` hook connects a `WebsocketProvider` to `mgrill-{session_id}` and observes the three Y collections. REST polling (3s) covers status/creator/turn_count only.
- **Turn model**: collaborative batched — participants append to a shared pending batch; any token-holder presses Send to AI, which bundles as `[Name]: <msg>` blocks and pushes to `mgrill:{id}:user_msgs`.
- **Voting**: appears only at `## FINAL PLAN`, per-tab `player_id` dedup (weak — UI surfaces this explicitly), Y.Map `votes`. Submit returns 409 on any `down` vote without `?override=true`; overrides are logged server-side but never prepended to the downstream task prompt.
- **Creator handoff**: 20s heartbeat, 60s absence threshold. Any token-holder can `POST /mgrill/{id}/claim-creator` past the threshold.

Full design notes, architecture diagram, and endpoint table: `docs/design-docs/multiplayer-grill.md`.

### Schedule ownership

When the server has no global `GITHUB_TOKEN`, schedule endpoints enforce per-user ownership. A SHA-256 hash of the creator's token is stored as `owner_token_hash` on each `ScheduledTask`. The frontend sends the user's token via `X-GitHub-Token` header on all schedule API calls. Set `ADMIN_GITHUB_TOKEN` env var to grant admin access to all schedules.

### Multiplayer Grill auth (server-GITHUB_TOKEN behaviour)

Chat participation (pending messages, send, vote, request plan) requires no GitHub token — anyone can join a session and contribute. Session **creation** still requires a token (`X-GitHub-Token` or server `GITHUB_TOKEN`). Creator-only actions (Submit, Keep Grilling, Heartbeat, Claim Creator) require a token and check creator identity.

| Server `GITHUB_TOKEN` | Client `X-GitHub-Token` | Chat / vote / add to batch | Create session | Submit / Keep Grilling / Heartbeat |
|-----------------------|--------------------------|----------------------------|----------------|-------------------------------------|
| unset                 | unset                    | yes                        | 401            | 401                                 |
| unset                 | set                      | yes                        | yes            | only the session creator (plus `ADMIN_GITHUB_TOKEN`) |
| **set**               | **unset**                | **yes**                    | **yes**        | **yes — anyone**                    |
| set                   | set                      | yes                        | yes            | yes — anyone                        |

Implementation hooks: `_mgrill_require_creator()` short-circuits when `_server_has_github_token()`, and `mgrill_poll` reports `is_creator=true` for everyone in server-token mode so the frontend unlocks creator UI. `ADMIN_GITHUB_TOKEN` still satisfies the creator check on a per-user basis when the server has no global token.

### Frontend persistence

GitHub tokens are persisted in `sessionStorage` (key `hh_github_token`) and auto-populated across all forms (task, schedule, Grill Me, issue) — session-scoped so the token does not survive closing the browser. A one-time migration in `loadGithubToken()` copies any legacy `localStorage` token into `sessionStorage` and removes it from `localStorage`. Other persisted UI state (task history, drafts, player name/color) intentionally remains in `localStorage`. Execution is always enabled (no checkbox). The model field auto-updates to the backend default when the backend selection changes.

## Code Conventions

- **Python 3.12+**, `uv` for package management
- **Formatter/linter**: `ruff` (line length 88, rules: E, W, F, I, N, UP, B, SIM, RUF)
- **Type hints everywhere**: prefer `X | None` over `Optional[X]`
- **Imports**: absolute (`from helping_hands.lib.config import Config`), grouped as stdlib → third-party → local
- **Naming**: `snake_case` functions/variables, `PascalCase` classes, `_` prefix for private helpers
- **Docstrings**: Google-style, required for public functions/classes
- **Tests**: pytest in `tests/`, coverage enabled by default in pytest config
- **No global state**: configuration is passed explicitly, no module-level singletons
- **Streaming-first**: AI responses should be streamable as they arrive

## Key Architectural Decisions

- Hand implementations stay split under `hands/v1/hand/` — avoid regressing to a monolithic `hand.py`
- Iterative hands preload `README.md`, `AGENT.md`, and bounded repo tree snapshot on iteration 1
- Git push uses token-authenticated (`GITHUB_TOKEN`) non-interactive remotes
- `owner/repo` CLI inputs are auto-cloned to temp workspaces
- `AGENT.md` is a living document that AI agents update as they learn repo conventions
- **Adding new task parameters** (checkboxes, inputs) requires updating ~15 files across frontend, API, Celery, hand, and schedules. Follow the checklist in `docs/design-docs/adding-task-parameters.md` — grep for `fix_ci` as the reference pattern.

## CI

GitHub Actions runs on Python 3.12/3.13/3.14: ruff lint + format check, pytest with coverage, Codecov upload. Frontend CI runs lint, typecheck, and Vitest with coverage separately.

## Deployment (LugiaWyvern)

The app deploys to a self-hosted GHA runner on lugiawyvern (`192.168.10.13`) via `.github/workflows/deploy-lugiawyvern.yml`. The deploy pulls latest code, syncs deps, and runs `./scripts/run-local-stack.sh stop && start` which launches server, worker, beat, flower, and frontend as background processes.

**Key pitfalls:**
- **`CI` env var must not leak into the Vite process.** GHA sets `CI=true` on all runners. The Vite config (`frontend/vite.config.ts`) skips the `/ws` WebSocket proxy when `CI` is set, which silently breaks all Yjs multiplayer (Hand World awareness, chat, decorations, multiplayer grill). The `run-local-stack.sh` frontend command uses `unset CI` inside its `bash -c` to prevent this.
- **GHA orphan process cleanup can kill services.** After a job completes, GHA's runner kills background processes it considers orphans. The deploy workflow sets `RUNNER_TRACKING_ID=""` in the step env block to prevent tracking. The permanent fix is `ACTIONS_RUNNER_KILL_ORPHANED_PROCESSES=false` in the runner's `.env` file (see `WAITING_ON.md`).
- **`start_service` PID tracking requires `exec`.** The function records `$$` then `exec`s the command. Using `env -u` or other wrappers that fork a child process breaks PID tracking — the recorded PID dies immediately and the service appears as "not running".
- **Top-level Vite proxy routes can silently fall through to the SPA fallback on lugia.** New backend route prefixes must be added to `frontend/vite.config.ts` proxy, but adding the entry isn't always sufficient: lugia's vite consistently failed to match a top-level `/version` prefix (returned the SPA `index.html`) despite an identical-looking entry being present and the same config working locally. A similar issue surfaced previously with the Flask + Vite setup. Workaround: nest new endpoints under a known-working prefix (e.g. `/health/version` instead of `/version`). Add to the proxy table anyway, but verify on lugia by curl-ing the path through port 5173 — if `Content-Type: text/html` comes back instead of JSON, it didn't match.
- **Module-level side effects in `vite.config.ts` may not run on lugia.** A top-level `writeFileSync` inside `vite.config.ts` ran reliably on local dev but did not run on lugia's `npx vite` invocation. Cause unresolved (suspect: vite-node config compilation cache). For anything that must run before vite starts (file generation, env setup), use a separate Node script invoked from `run-local-stack.sh` ahead of `exec npx vite`. See `frontend/scripts/write-version.mjs` as the reference pattern.
- **Celery `signal.connect` defaults to `weak=True`.** Handlers defined as nested closures inside a setup function are garbage-collected the moment that function returns, silently detaching the signal. Define handlers at module level and pass `weak=False` explicitly when subscribing to `worker_ready`, `heartbeat_sent`, etc.
- **GHA-launched workers don't inherit your shell's PATH for `claude`/`codex`/`goose`/`gemini`.** When the deploy workflow exec's `run-local-stack.sh start`, the worker sees the GHA runner's PATH — not the login-shell PATH that has `~/.npm-global/bin` (or wherever `npm prefix -g`/bin points). Symptom: subprocess calls like `claude -p ...` fail with `FileNotFoundError`, surfaced in the UI as misleading "Claude Code CLI not installed or not on PATH" errors mid-session even though the binary IS installed. `run-local-stack.sh` has an `augment_path_for_cli_hands` helper that prepends `npm prefix -g`/bin and common fallbacks; new CLI hands should keep working as long as their binary lives in one of those directories. Diagnostic: `report_cli_hand_availability` runs at the start of `start_all` and logs `CLI hands available: …` / `CLI hands NOT on PATH: …` so a missing binary is visible at deploy time, not at first grill request.

## Tracking files

- `HUMAN_INTENT.md` — active user intents/desires (what the user wants, not implementation details)
- `WAITING_ON.md` — items blocked on external input or manual action
- Neither file should accumulate completed items — remove them once done.

## Test guidelines
- Don't write tests that assert exact markdown formatting, punctuation, or doc prose style
- Don't use `inspect.getsource()` to check syntax choices — test behavior instead
- Doc structure tests should verify files exist and are indexed, not enforce cosmetic rules