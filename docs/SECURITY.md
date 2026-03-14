# Security

Security considerations for helping_hands.

## Sensitive data

- **GitHub tokens**: Read from `GITHUB_TOKEN` / `GH_TOKEN` env vars, never
  logged or stored in config files.
- **API keys**: Loaded from `.env` files via python-dotenv, not committed.
- **`.env` files**: Listed in `.gitignore`. `.env.example` has placeholder
  values only.

## Subprocess execution

CLI hands (ClaudeCodeHand, CodexCLIHand, GeminiCLIHand) run external CLIs as
subprocesses:

- Commands are built from config, not user input — no injection risk from
  prompts.
- Environment is explicitly controlled; only necessary vars are passed.
- Subprocess timeout prevents runaway processes.

## Code execution

- Hands propose code changes but do not execute arbitrary code.
- In CLI mode, the user reviews and approves changes.
- In app mode, the Celery worker runs the hand in an isolated task.

## Dependencies

- Optional dependency groups (`langchain`, `atomic`, `server`, etc.) are
  installed only when needed, reducing attack surface.
- Pre-commit hooks run ruff to catch common issues.
