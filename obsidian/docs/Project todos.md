# Project todos

The canonical checklist lives in the repo root: **`TODO.md`**. This note is for design notes or decisions that affect the todos.

## Summary (from TODO.md)

All major milestones are complete. Two CI items remain intentionally deferred:

1. **Set up Python project** — complete (layout, tooling, CI/CD, tests)
2. **Dockerise app mode** — complete (Dockerfile, Compose, all services)
3. **Autodocs** — complete (MkDocs Material + mkdocstrings, 36 API pages, GitHub Pages)
4. **Hand backends** — complete (E2E, iterative, all 4 CLI hands, cron scheduling, hardening)
5. **MCP server** — complete (filesystem, execution, web, build, config tools)
6. **Skills system** — complete (normalization, validation, prompt injection)
7. **React frontend** — complete (task submission, monitoring, world view)
8. **Additional features** — complete (PR description, verbose logging, config/API validation, exception hardening)

**Deferred:**
- CI type check step: `ty` is in pre-commit but lacks a stable non-hook CI runner
- Build/publish pipeline: project is pre-1.0 beta

## Design notes

Key architectural decisions and implementation notes. For the full list of recurring decisions, see the root [`AGENT.md`](../../AGENT.md).

### Core execution model

- Hand internals split into a package module (`lib/hands/v1/hand/`); avoid regressing to monolithic `hand.py`.
- Basic iterative backends default to a final commit/push/PR step; `--no-pr` disables side effects (maps to dry-run for E2E).
- Iterative hands preload iteration-1 context from `README.md`, `AGENT.md`, and a bounded file-tree snapshot.
- Provider routing centralized in `lib/ai_providers/` + `model_provider.py`; five providers: openai, anthropic, google, litellm, ollama.
- System file operations route through `lib/meta/tools/filesystem.py` for path safety; MCP filesystem tools share the same layer.

### E2E and PR semantics

- E2E PR updates are **state refresh**: live runs update both PR body and marker comment with latest timestamp/commit/prompt.
- Branch collision handling: switch to existing branch instead of failing.
- Draft PR mode (`HELPING_HANDS_DRAFT_PR`), idempotency guard (`find_open_pr_for_branch`).
- GitHub API calls wrapped with `GithubException` handling — clear error messages with actionable hints.

### CLI backends

- All four CLI backends (`codexcli`, `claudecodecli`, `goose`, `geminicli`) fully implemented with two-phase subprocess flow, streaming, heartbeat/idle-timeout controls.
- `claudecodecli`: edit-enforcement retry, `npx` fallback, non-interactive permissions skip.
- `goose`: auto-derived `GOOSE_PROVIDER`/`GOOSE_MODEL`, auto-injected `--with-builtin developer`.
- `geminicli`: `--approval-mode auto_edit`, model-unavailable retry.

### App mode and scheduling

- Compose file is `compose.yaml` with default in-network Redis/Celery URLs when `.env` is sparse.
- Monitoring: JS polling + no-JS fallback with fixed-size monitor cells.
- Cron scheduling via `ScheduleManager` (RedBeat + Redis metadata) with CRUD endpoints.
- React frontend wraps task submission/monitoring with backend selection, world view, and keyboard navigation.

### Validation and observability

- `Config.__post_init__` validates repo format and model name patterns.
- `BuildRequest`/`ScheduleRequest` validate input at the API boundary (bounds, cron syntax).
- Health check exceptions logged at warning level with `exc_info=True`.
- CLI `--verbose` wires to `logging.basicConfig()`; silent exception blocks use `logger.debug()`.

### Documentation and testing

- MkDocs: 36 API doc pages covering all 13 Hand modules (12 implementation + 1 package surface) plus backward-compat shim and all subsystems.
- Docstrings: Google-style on all public methods; `_TwoPhaseCLIHand`, `AIProvider`, and all `run()`/`stream()` methods documented.
- Tests: 510 tests covering filesystem (40), CLI hands (75+), schedule manager (22), Celery helpers (15), skills (30+4 config validation), MCP (17), server app (47), AI providers (28).
- PEP 561: `py.typed` marker + `Typing :: Typed` classifier in `pyproject.toml`.
