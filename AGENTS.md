# AGENTS.md — Multi-agent coordination for helping_hands

> How multiple AI agents (hands) collaborate on this repo.

## Agent types

| Agent | Backend | Status | Use case |
|---|---|---|---|
| LangGraphHand | LangChain / LangGraph | Implemented | Full agent loop with tool use |
| AtomicHand | atomic-agents | Implemented | Structured output agent |
| ClaudeCodeHand | Claude Code CLI | Implemented | Subprocess CLI agent |
| CodexCLIHand | Codex CLI | Implemented | Subprocess CLI agent |
| GeminiCLIHand | Gemini CLI | Implemented | Subprocess CLI agent |
| E2EHand | CI test runner | Active | End-to-end validation |

## Backend selection

Set the backend via CLI flag or config:

```bash
# CLI flag
helping-hands <repo> --backend claudecode

# Environment variable
HELPING_HANDS_BACKEND=langgraph

# .helping_hands.toml
[helping_hands]
backend = "claudecode"
```

Valid values: `langgraph`, `atomic`, `claudecode`, `codexcli`, `geminicli`.

## Agent coordination patterns

1. **Single-hand mode** (default): One hand operates on the repo per session.
2. **E2E mode**: A hand runs non-interactively via CI to validate the pipeline.
3. **App mode** (planned): Multiple hands run as Celery workers, each picking
   up tasks from the queue.

## Hand lifecycle

1. **Config** — Backend is selected, config is loaded.
2. **Ingest** — Repo is cloned/indexed, context is built.
3. **Run/Stream** — Hand receives prompt, calls AI, returns response.
4. **Record** — Preferences discovered are written to AGENT.md.

## Guidelines for hands

- Follow `AGENT.md` for code style and design preferences.
- Keep diffs small and focused.
- Always include tests with new functionality.
- Update documentation when behaviour changes.
