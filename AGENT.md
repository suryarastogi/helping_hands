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

- **Language**: Python 3.11+
- **Package manager**: uv (`uv sync`, `uv run`, `uv add`)
- **Formatter**: `ruff format` (line length 88)
- **Linter**: `ruff check` (rules: E, W, F, I, N, UP, B, SIM, RUF)
- **Type checker**: ty (config in `pyproject.toml`)
- **Pre-commit**: ruff lint + format via `.pre-commit-config.yaml`
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
- **Tests**: pytest, under `tests/`. Run with `uv run pytest -v`.

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

*No decisions recorded yet.*

## Dependencies `[auto-update]`

<!-- Agents: keep this in sync with requirements.txt. Note why each
     dependency exists so future agents don't accidentally remove
     something important. -->

| Package | Group | Purpose |
|---|---|---|
| pytest | dev | Test runner |
| ruff | dev | Linter + formatter |
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
| mcp[cli] | mcp / dev | MCP Python SDK for the MCP server |
| mkdocs-material | docs | Documentation site theme |
| mkdocstrings[python] | docs | Auto-generate API docs from docstrings |

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

*Last updated: 2026-02-21 — MCP server (mcp_server.py), mcp extra, Docker/Compose service.*
