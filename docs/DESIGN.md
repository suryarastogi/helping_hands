# Design

See [design-docs/](design-docs/index.md) for detailed design documents and
[ARCHITECTURE.md](../ARCHITECTURE.md) for system architecture.

## Key decisions

1. **Hand protocol** — All backends implement `run()` + `stream()`. This
   allows backend-agnostic code in CLI, server, and MCP layers.

2. **Config cascade** — CLI flags > env vars > `.env` files > defaults.
   No global state; `Config` is an immutable dataclass passed explicitly.

3. **Subprocess CLI hands** — Claude Code, Codex, and Gemini backends run
   their respective CLIs as subprocesses rather than importing SDKs. This
   keeps dependencies optional and isolated.

4. **Repo-first context** — Every hand session starts with repo ingestion.
   The hand gets structural context (file tree, conventions) before any
   AI interaction.
