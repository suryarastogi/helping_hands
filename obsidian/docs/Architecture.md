# Architecture

High-level view of how helping_hands is built. For file layout and config, see the repo README.

## Runtime surfaces (current)

The project currently exposes three runtime surfaces:

- **CLI mode (implemented)** — `helping-hands <repo>` indexes a local repo. `helping-hands <owner/repo> --e2e` runs full clone/edit/commit/push/PR workflow.
- **App mode (implemented baseline)** — FastAPI + Celery integration exists. `/build` enqueues `build_feature`; workers run `E2EHand`; `/tasks/{task_id}` reports status/result.
- **MCP mode (implemented baseline)** — MCP server exposes tools for repo indexing, build enqueue/status, file read, and config inspection.

App-mode foundations are present (server, worker, broker/backend wiring), while product-level scheduling/state workflows are still evolving.

## Layers (shared)

1. **Config** (`Config.from_env`) — Loads `.env` from cwd and target repo (when local), merges env + CLI overrides.
2. **Repo index** (`RepoIndex`) — Builds a file map from local repos; in E2E flow, repo content is acquired via Git clone first.
3. **Hand backend** (`Hand` + implementations) — Common protocol with concrete `E2EHand`; `LangGraphHand` and `AtomicHand`; CLI-specific scaffold hands.
4. **GitHub integration** (`GitHubClient`) — Clone/branch/commit/push plus PR create/read/update and marker-based status comment updates.
5. **Entry points** — CLI, FastAPI app, and MCP server orchestrate calls to the same core.

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
  default mode: Config → RepoIndex → ready/indexed output
  --e2e mode:   Config → E2EHand → GitHubClient → branch/PR updates
```

## Data flow (app mode baseline)

```
User/Client → FastAPI /build → Celery queue
                               ↓
                        worker task build_feature
                               ↓
                         E2EHand.run(...)
                               ↓
                 task result available via /tasks/{task_id}
```

## Design principles

- **Plain data between layers** — Dicts or dataclasses, not tight coupling. Easier to test and swap implementations.
- **Streaming by default** — AI output streams to the terminal; no "wait for full response" unless needed.
- **Explicit config** — No module-level singletons. Config is loaded once and passed in.
- **Idempotent-ish E2E updates** — PR resume path updates existing branch, PR body, and status comment.

These are also reflected in the repo's [[AGENT.md]] under Design preferences.

## CI controls relevant to architecture

- Live E2E integration test is opt-in (`HELPING_HANDS_RUN_E2E_INTEGRATION=1`).
- In CI matrix, only `master` + Python `3.13` performs live push/update; other versions run E2E in dry-run to avoid branch push races.
- Pre-commit enforces `ruff`, `ruff-format`, and `ty` (currently scoped to `src` with targeted ignores for known optional-backend noise).
