# Agents

> Conventions for AI agents working on this repo. For detailed agent behavior, see [AGENT.md](AGENT.md).

## Agent Types

| Agent | Entry Point | Purpose |
|-------|-------------|---------|
| helping_hands CLI | `uv run helping-hands` | AI-driven code changes via Hand backends |
| Claude Code | `claude` | Interactive dev assistant (reads CLAUDE.md) |
| MCP clients | `uv run helping-hands-mcp` | Tool-use via Model Context Protocol |

## Coordination

- **AGENT.md** is the living document agents update with conventions and decisions
- **CLAUDE.md** provides build commands and architecture context for Claude Code
- Agents should read both files before making changes
- When making design decisions, record them in AGENT.md's "Recurring decisions" section

## Execution Plans

Active plans live in `docs/exec-plans/active/`. When complete, move to `docs/exec-plans/completed/`. Plans track multi-session work that spans beyond a single agent run.

## Agent Workflow

1. Read AGENT.md and CLAUDE.md for context
2. Check `docs/exec-plans/active/` for in-progress plans
3. Execute the most actionable items
4. Update plan status (check off completed items)
5. If all items done, move plan to `completed/`
6. Update AGENT.md if new conventions were discovered
