<p align="center">
  <img src="media/banner.png" alt="helping_hands" />
</p>

<p align="center">
  <a href="https://codecov.io/gh/suryarastogi/helping_hands">
    <img src="https://codecov.io/gh/suryarastogi/helping_hands/graph/badge.svg" alt="Coverage" />
  </a>
</p>

---

## What is this?

`helping_hands` is a Python tool that takes a git repository as input, understands its structure and conventions, and collaborates with you to add features, fix bugs, and evolve the codebase using AI. It can run in **CLI mode** (interactive in the terminal) or **app mode** (server with background workers).

### Modes

- **CLI mode** (default) — Run `helping_hands <repo>` or `helping_hands <owner/repo>`. You can index only, or run iterative backends (`basic-langgraph`, `basic-atomic`, `basic-agent`) with streamed output.
- **App mode** — Runs a FastAPI server plus a worker stack (Celery, Redis, Postgres) so jobs run asynchronously and on a schedule (cron). Includes Flower for queue monitoring. Use when you want a persistent service, queued or scheduled repo-building tasks, or a UI.

### Execution flow

- **Server mode**: `server -> enqueue hand task -> hand executes`
- **CLI mode**: `cli -> hand executes`

For asynchronous runs, the hand UUID is the Celery task ID. For synchronous
runs, UUIDs are generated in-hand as needed.

- `E2EHand` uses `{hand_uuid}/git/{repo}` workspace layout and supports
  new PR creation plus resume/update via `--pr-number`.
- Basic iterative hands (`basic-langgraph`, `basic-atomic`) operate on the
  target repo context and, by default, attempt a final commit/push/PR step.
  Disable with `--no-pr`.
- Iterative basic hands can request file contents using `@@READ: path` and
  apply edits using `@@FILE` blocks in-model.
- System filesystem actions for hands (path-safe read/write/mkdir checks) are
  centralized in `lib/meta/tools/filesystem.py`.
- Provider-level wrappers and model/env defaults are centralized in
  `lib/ai_providers/` (`openai`, `anthropic`, `google`, `litellm`).
- Push uses token-authenticated GitHub remote configuration and disables
  interactive credential prompts.

### Key ideas

- **Repo-aware**: Clones or reads a local repo, indexes the file tree, and builds context so the AI understands what it's working with.
- **Conversational building**: Describe what you want in plain language. The agent proposes changes, writes code, and iterates with you.
- **Convention-respectful**: Learns the repo's patterns (naming, structure, style) and follows them in generated code.
- **Self-improving guidance**: Ships with an `AGENT.md` file that the agent updates over time as it learns your preferences for tone, style, and design.
- **E2E validation hand**: `E2EHand` is a minimal concrete hand used to test
  the full clone/edit/commit/push/PR flow.
- **Iterative basic hands**: `basic-langgraph` and `basic-atomic` run
  stepwise implementation loops with live streaming, interruption, and optional
  final PR creation.

## Quick start
