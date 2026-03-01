# Vision

**helping_hands** is a Python tool that turns a git repo into a collaborative build environment. You point it at a codebase; an AI "hand" understands the repo and helps you add features, fix bugs, and evolve the code in conversation. It can run as a **CLI** (interactive in the terminal), as an **app** (server + background workers for async and scheduled jobs), or as an **MCP server** (exposing repo indexing, build, filesystem, execution, and web tools to MCP-compatible clients).

## Why

- **Context is everything.** Generic AI assistants don't know your project's structure, naming, or conventions. helping_hands ingests the repo first so the AI works *inside* your world.
- **Conversation over one-shot prompts.** Building a feature is iterative: plan → implement → review → refine. The tool is built for that loop.
- **Preferences persist.** Session learnings (tone, style, design choices) are written back into [[AGENT.md]] so the next session—and the next hand—starts smarter.

## Success looks like

- A user clones any repo, runs `helping_hands <repo>` (CLI), uses the app (server + workers), or connects via MCP, describes what they want in plain language, and gets coherent, convention-following changes.
- Hands and humans both contribute to the [[Project Log]] so the project's history is a shared log of what happened and who (or what) did it.

## Non-goals (for now)

- Replacing the human in the loop; the human reviews and approves.
- Supporting non-git workflows.
- Being a generic chatbot; the focus is repo building, not Q&A about unrelated topics.
