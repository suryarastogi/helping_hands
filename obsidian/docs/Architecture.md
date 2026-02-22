# Architecture

High-level view of how helping_hands is built. For file layout and config, see the repo README.

## Runtime surfaces (current)

The project currently exposes three runtime surfaces:

- **CLI mode (implemented)** — supports local path or `owner/repo` input. Can run index-only, E2E, iterative basic backends (`basic-langgraph`, `basic-atomic`, `basic-agent`), and `codexcli`.
- **App mode (implemented)** — FastAPI + Celery integration supports `e2e`, `basic-langgraph`, `basic-atomic`, and `basic-agent`. `/build` enqueues `build_feature`; `/tasks/{task_id}` returns JSON status/result; `/monitor/{task_id}` provides an auto-refresh no-JS monitor page.
- **MCP mode (implemented baseline)** — MCP server exposes tools for repo indexing, build enqueue/status, filesystem operations (`read_file`, `write_file`, `mkdir`, `path_exists`), and config inspection.

App-mode foundations are present (server, worker, broker/backend wiring), while product-level scheduling/state workflows are still evolving.

## Layers (shared)

1. **Config** (`Config.from_env`) — Loads `.env` from cwd and target repo (when local), merges env + CLI overrides.
2. **Repo index** (`RepoIndex`) — Builds a file map from local repos; in E2E flow, repo content is acquired via Git clone first.
3. **Hand backend** (`Hand` + implementations) — Common protocol with `E2EHand`, `LangGraphHand`, `AtomicHand`, basic iterative hands, plus CLI scaffold hands.
   - Current code shape is a package module: `lib/hands/v1/hand/` (`base.py`, `langgraph.py`, `atomic.py`, `iterative.py`, `e2e.py`, `placeholders.py`, `__init__.py` export surface).
4. **AI provider wrappers** (`lib.ai_providers`) — Provider-specific wrappers (`openai`, `anthropic`, `google`, `litellm`) with a common interface and lazy `inner` client/library.
5. **Model adapter layer** (`lib/hands/v1/hand/model_provider.py`) — Resolves model strings (including `provider/model`) into backend-adapted runtime clients for LangGraph/Atomic hands.
6. **System tools layer** (`lib.meta.tools.filesystem`) — Shared path-safe file operations (`read_text_file`, `write_text_file`, `mkdir_path`, path resolution/validation) consumed by iterative hands and MCP filesystem tools.
7. **GitHub integration** (`GitHubClient`) — Clone/branch/commit/push plus PR create/read/update and marker-based status comment updates.
8. **Entry points** — CLI, FastAPI app, and MCP server orchestrate calls to the same core.

## Finalization workflow (all hands)

Hands now share a finalization helper that runs by default unless explicitly disabled:

1. Detect in-repo git state and pending changes.
2. Resolve GitHub repo from `origin`.
3. Create branch, commit changes, push using token-authenticated non-interactive remote config.
4. Open PR with generated summary body.

CLI flag `--no-pr` disables this final step for iterative/basic backends and maps to dry-run in E2E mode.

## Iterative bootstrap context (basic hands)

`BasicLangGraphHand` and `BasicAtomicHand` prepend iteration-1 prompt context with:

1. `README.md`/`readme.md` content when present.
2. `AGENT.md`/`agent.md` content when present.
3. A bounded repository tree snapshot (depth/entry limited).

This reduces first-iteration drift and gives the model conventions/context before it asks for additional `@@READ` data.

## Codex CLI backend requirements

`codexcli` uses the external `codex` executable from the user environment.
Requirements:

1. `codex` CLI installed and available on `PATH`.
2. Authenticated codex session (`codex login`) or equivalent API-key setup in the shell.
3. `GITHUB_TOKEN` or `GH_TOKEN` present if final commit/push/PR is expected.
4. Access to the selected model (`gpt-5.2` is the backend default when model is unset/default).
5. Current scope is CLI-only; app-mode backend routing does not include `codexcli`.

## E2E workflow (source of truth)

`E2EHand` currently drives the production-tested path:

1. Resolve workspace root: `{HELPING_HANDS_WORK_ROOT}/{hand_uuid}/git/{safe_repo}`.
2. Resolve base/head:
   - New PR path: new branch `helping-hands/e2e-{uuid8}` from base.
   - Resume path (`pr_number`): fetch PR metadata, checkout existing head.
3. Write `HELPING_HANDS_E2E.md` marker with UTC timestamp and prompt.
4. Live mode only:
   - set local git identity
   - commit + push
   - create PR if needed
   - **always update PR body** with latest timestamp/commit/prompt
   - **always upsert a marker-tagged PR comment** (`<!-- helping_hands:e2e-status -->`)

This makes reruns deterministic: existing PR description and status comment are refreshed instead of accumulating stale state.

## Data flow (CLI)

```
User → CLI
  index mode:    Config → RepoIndex → ready/indexed output
  basic backend: Config → Basic*Hand iterative stream → optional final PR
  --e2e mode:    Config → E2EHand → GitHubClient → branch/PR updates
```

## Data flow (app mode baseline)

```
User/Client → FastAPI /build → Celery queue
                               ↓
                       worker task build_feature
                               ↓
          backend routing (E2EHand / BasicLangGraphHand / BasicAtomicHand)
                               ↓
      task status/result available via /tasks/{task_id} (JSON)
      no-JS monitor available via /monitor/{task_id} (HTML auto-refresh)
```

## Design principles

- **Plain data between layers** — Dicts or dataclasses, not tight coupling. Easier to test and swap implementations.
- **Streaming by default** — AI output streams to the terminal; no "wait for full response" unless needed.
- **Explicit config** — No module-level singletons. Config is loaded once and passed in.
- **Idempotent-ish E2E updates** — PR resume path updates existing branch, PR body, and status comment.
- **Explicit side-effect toggle** — PR side effects default on; disable with `--no-pr`.

These are also reflected in the repo's [[AGENT.md]] under Design preferences.

## CI controls relevant to architecture

- Live E2E integration test is opt-in (`HELPING_HANDS_RUN_E2E_INTEGRATION=1`).
- In CI matrix, only `master` + Python `3.13` performs live push/update; other versions run E2E in dry-run to avoid branch push races.
- CI test runs now include `pytest-cov` coverage reporting and produce `coverage.xml`; Python `3.12` job uploads coverage to Codecov.
- Pre-commit enforces `ruff`, `ruff-format`, and `ty` (currently scoped to `src` with targeted ignores for known optional-backend noise).
- Compose runtime wiring now provides sane defaults for app-mode service env when `.env` is sparse:
  - `REDIS_URL=redis://redis:6379/0`
  - `CELERY_BROKER_URL=redis://redis:6379/0`
  - `CELERY_RESULT_BACKEND=redis://redis:6379/1`
