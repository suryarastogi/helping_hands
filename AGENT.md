# AGENT.md — Guidance for AI agents working on this repo

> **This file is living documentation.** Agents should update it as they learn
> the repo's conventions, the maintainer's preferences, and recurring patterns.
> Every section marked with `[auto-update]` is a candidate for revision at the
> end of a session.

For project purpose, structure, configuration, and workflow, see
[README.md](README.md). This file covers **how to work on the code**, not
what the code does.

---

## Ground rules

1. **Read before you write.** Always understand the surrounding code and
   conventions before proposing changes.
2. **Match existing style.** When in doubt, mimic the patterns already present
   in the file or module you're editing.
3. **Small, reviewable diffs.** Prefer focused changes over large rewrites.
4. **Tests accompany features.** New functionality should include tests.
5. **Update this file.** If you discover a preference, convention, or
   recurring pattern that future agents should know, record it here.

---

## Code style `[auto-update]`

<!-- Agents: update this section when you notice consistent style choices. -->

- **Language**: Python 3.12+
- **Package manager**: uv (`uv sync`, `uv run`, `uv add`)
- **Formatter**: `ruff format` (line length 88)
- **Linter**: `ruff check` (rules: E, W, F, I, N, UP, B, SIM, RUF)
- **Type checker**: ty (config in `pyproject.toml`)
- **Pre-commit**: ruff lint + format + ty via `.pre-commit-config.yaml`
- **Type hints**: Use them everywhere; prefer `X | None` over `Optional[X]`.
- **Imports**: Group as stdlib → third-party → local, separated by blank lines.
  Use absolute imports (`from helping_hands.lib.config import Config`).
- **Naming**:
  - `snake_case` for functions, variables, modules.
  - `PascalCase` for classes.
  - Private helpers prefixed with `_`.
- **Docstrings**: Google-style. Required for public functions and classes.
  Omit for obvious private helpers.
- **Comments**: Only when the *why* isn't obvious from the code. Never
  narrate what the code does.
- **Tests**: pytest, under `tests/`. Coverage reporting is enabled in pytest
  defaults; run with `uv run pytest -v` (or add `--cov-report=xml` when needed).

## Design preferences `[auto-update]`

<!-- Agents: update this section when the maintainer makes design decisions
     that should carry forward (e.g., "always use dataclasses over dicts
     for config", "prefer composition over inheritance"). -->

- **Separation of concerns**: Repo handling, AI interaction, and CLI are
  distinct modules. They communicate through plain data (dicts, dataclasses),
  not by importing each other's internals.
- **No global state**: Configuration is passed explicitly; no module-level
  singletons.
- **Streaming-friendly**: AI responses should be streamable to the terminal
  as they arrive.

## Tone and communication `[auto-update]`

<!-- Agents: update this section when the maintainer expresses preferences
     about how generated output (commit messages, PR descriptions, code
     comments, docstrings) should read. -->

- Keep language **concise and direct**. Avoid filler words.
- Commit messages: imperative mood, single line under 72 chars, optional body
  separated by a blank line.
- PR descriptions: short summary + bullet list of changes + test plan.
- Code comments: terse. Explain *why*, not *what*.

## Recurring decisions `[auto-update]`

<!-- Agents: log decisions here so they don't get re-debated. Format:
     - **Topic**: Decision (date or session reference) -->

- **Final PR behavior**: Hands should attempt a final commit/push/PR by default, with explicit opt-out (`--no-pr`) when side effects must be disabled. (2026-02-22)
- **CLI repo input**: Non-E2E CLI runs accept local paths and `owner/repo` GitHub references; `owner/repo` is cloned to a temp workspace automatically. (2026-02-22)
- **Push auth**: Git pushes for finalization should be token-authenticated and non-interactive to avoid OS credential popups in automation. (2026-02-22)
- **Hand module layout**: Keep hand implementations split under `src/helping_hands/lib/hands/v1/hand/` with `__init__.py` as public export surface; avoid regressing to a monolithic `hand.py`. (2026-02-22)
- **System tool reuse**: Repo file operations for hands should use shared helpers in `src/helping_hands/lib/meta/tools/filesystem.py` for path-safe behavior and consistent semantics; MCP filesystem tools should route through the same layer. (2026-02-22)
- **Provider abstraction**: Resolve models through `src/helping_hands/lib/ai_providers/` plus `src/helping_hands/lib/hands/v1/hand/model_provider.py` adapters, instead of hard-coding provider clients in hands. (2026-02-22)
- **Iterative bootstrap context**: `BasicLangGraphHand` and `BasicAtomicHand` should preload iteration-1 prompt context from `README.md`, `AGENT.md`, and a bounded repo tree snapshot when available. (2026-02-22)
- **Default OpenAI-family model**: Prefer `gpt-5.2` as the default fallback model in provider wrappers/examples unless explicitly overridden by config. (2026-02-22)
- **CLI backend completeness**: All four CLI-backed hands (`codexcli`, `claudecodecli`, `goose`, `geminicli`) are fully implemented with two-phase subprocess flow, streaming, heartbeat/idle-timeout controls, and final PR integration. (2026-02-28)
- **Cron scheduling**: Server supports cron-scheduled submissions via `ScheduleManager` (RedBeat + Redis metadata) with CRUD API endpoints. (2026-02-28)
- **GitHub API error handling**: All PyGithub API calls in `github.py` should be wrapped with `GithubException` handling that produces clear error messages with HTTP status and actionable hints. (2026-03-01)
- **E2E idempotency**: E2EHand handles branch collisions (switch to existing), supports draft PRs (`HELPING_HANDS_DRAFT_PR`), and detects/reuses existing open PRs for the same head branch. (2026-03-01)
- **Config input validation**: `Config.__post_init__` validates `repo` format (filesystem path or `owner/repo`) and warns on unexpected `model` name patterns. (2026-03-01)

## Dependencies `[auto-update]`

<!-- Agents: keep this in sync with requirements.txt. Note why each
     dependency exists so future agents don't accidentally remove
     something important. -->

| Package | Group | Purpose |
|---|---|---|
| pytest | dev | Test runner |
| pytest-cov | dev | Coverage reporting for pytest (terminal + XML) |
| ruff | dev | Linter + formatter |
| ty | dev | Type checker used in pre-commit |
| pre-commit | dev | Git hook manager |
| fastapi | server | HTTP/WS API for app mode |
| uvicorn | server | ASGI server |
| celery[redis] | server | Task queue + Redis broker |
| flower | server | Celery monitoring UI |
| psycopg2-binary | server | Postgres driver |
| langchain-openai | langchain | LangChain LLM wrapper for LangGraphHand |
| langgraph | langchain | Agent graph framework for LangGraphHand |
| atomic-agents | atomic | Atomic Agents framework for AtomicHand (Python 3.12+) |
| instructor | atomic | Structured LLM output for atomic-agents |
| openai | atomic | OpenAI client for atomic-agents |
| PyGithub | github / dev | GitHub API client for auth, clone, PRs (used by agents as a tool) |
| mcp[cli] | mcp / dev | MCP Python SDK for the MCP server |
| mkdocs-material | docs | Documentation site theme |
| mkdocstrings[python] | docs | Auto-generate API docs from docstrings |
| celery-redbeat | server | Redis-backed cron scheduler for Celery Beat |
| croniter | server | Cron expression parsing and next-run calculation |
| redis | server | Redis client (used by ScheduleManager for metadata persistence) |
| python-dotenv | runtime | Loads `.env` values into process env for config/hand setup |

---

## How to update this file

At the end of each session, review the `[auto-update]` sections and ask:

1. **Did I learn something new about the codebase's conventions?** Update
   *Code style*.
2. **Did the maintainer express a preference about tone, naming, or design?**
   Update *Tone and communication* or *Design preferences*.
3. **Did we make a decision that future sessions should respect?** Add it to
   *Recurring decisions*.
4. **Did dependencies change?** Update the *Dependencies* table.

When making updates:
- Keep entries **concise** — one or two sentences max.
- Include a date or context reference so the reasoning is traceable.
- Never remove an entry unless it's explicitly superseded; instead mark it
  as deprecated with a note.

---

*Last updated: 2026-03-01 — production robustness: GitHub API error handling, E2E hardening (branch collision, draft PR, idempotency), config validation.*
