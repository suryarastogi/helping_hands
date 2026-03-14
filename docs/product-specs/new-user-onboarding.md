# New user onboarding

## Goal

A user can go from `git clone` to a working helping_hands session in under
5 minutes, with any supported backend.

## Steps

1. **Clone and install**: `git clone ... && cd helping_hands && uv sync --dev`
2. **Configure**: Copy `.env.example` to `.env`, set API keys for chosen backend.
3. **Run CLI**: `uv run helping-hands <repo> --backend claudecode`
4. **See output**: Hand indexes the repo, confirms readiness, accepts prompts.

## Backend requirements

| Backend | Required env vars |
|---|---|
| `langgraph` | `OPENAI_API_KEY` |
| `atomic` | `OPENAI_API_KEY` |
| `claudecode` | Claude Code CLI installed, `HELPING_HANDS_CLAUDE_CLI_CMD` (optional) |
| `codexcli` | Codex CLI installed, `HELPING_HANDS_CODEX_CLI_CMD` (optional) |
| `geminicli` | Gemini CLI installed, `HELPING_HANDS_GEMINI_CLI_CMD` (optional) |

## Success criteria

- [ ] User can select any implemented backend via `--backend` flag.
- [ ] Clear error message when backend dependencies are missing.
- [ ] `uv run helping-hands --help` shows all options including `--backend`.
