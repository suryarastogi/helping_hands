# Core beliefs

Foundational principles that guide helping_hands design and development.

## 1. Context is everything

Generic AI assistants don't know your project. helping_hands ingests the repo
first so the AI works *inside* your codebase — with knowledge of file layout,
naming conventions, and architecture.

## 2. Conversation over one-shot prompts

Building features is iterative: plan, implement, review, refine. The tool is
built for that loop, not single-prompt generation.

## 3. Preferences persist

Session learnings (tone, style, design choices) are written back into
`AGENT.md` so the next session starts smarter. The project accumulates
institutional knowledge.

## 4. Backend-agnostic

The `Hand` protocol means any AI backend can be plugged in. LangGraph, Atomic,
Claude Code CLI, or future backends — same interface, same context.

## 5. Human in the loop

The human reviews and approves. Hands propose; humans decide. This is a
collaboration tool, not an autonomous agent.

## 6. Plain data between layers

Dicts and dataclasses flow between components. No tight coupling, no ORM
sprawl. Easy to test, easy to swap implementations.
