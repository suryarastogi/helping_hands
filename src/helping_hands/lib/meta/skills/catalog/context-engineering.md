# Context Engineering

Optimize how you gather and use repository context to maximize result quality with minimal token footprint:

## Before Writing Code
1. **Read the README and AGENT.md first** — understand project conventions, build commands, and architecture before making changes.
2. **Use bounded tree snapshots** — list directory structure to orient yourself, but limit depth to avoid token waste.
3. **Search before reading** — use grep/glob to find relevant files instead of reading entire directories sequentially.
4. **Read narrowly** — read only the functions/classes you need to modify, not entire files when they are large.

## While Writing Code
5. **Follow existing patterns** — match the style, naming conventions, and architectural patterns already in the codebase rather than introducing new ones.
6. **Check imports** — verify that modules you reference actually exist and are imported correctly.
7. **Validate incrementally** — run linters or type checkers after significant changes rather than waiting until the end.

## Context Prioritization
- **High value**: README, AGENT.md, existing tests for the module you're changing, the file you're editing, direct imports/dependencies.
- **Medium value**: CI config, related modules, package.json/pyproject.toml for available commands.
- **Low value**: Unrelated modules, documentation files, vendored dependencies.

## Token Efficiency
- Summarize large outputs (test results, build logs) rather than carrying raw output through the conversation.
- When searching, use specific patterns instead of broad queries.
- Prefer `git grep` over full-repo grep when the repo has a git history — it skips untracked/generated files.
