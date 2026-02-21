# Concepts

Core ideas that define helping_hands. The README has the short version; this note expands for design and onboarding.

## Hands

A **hand** is an AI helper in this framework. It's the agent that reads the repo, reasons about the codebase, proposes changes, and iterates with you. Hands can also contribute to project docs—for example, adding entries to the [[Project Log]]—so their work is visible and traceable.

When you see "hand" in these docs, it means "the AI agent acting in a helping_hands session."

## Repo-aware

The tool doesn't guess: it **ingests** the target repo (clone if remote, or read from a local path), walks the file tree, and builds a structural map. That context is what the hand gets. So the AI knows file layout, key entry points, and—over time—conventions from [[AGENT.md]].

## Convention-respectful

Generated code should match the repo it's being added to. That means following existing naming, style, and architecture. AGENT.md in the *target* repo (the one you're building) can be updated by the hand to record what it learned; the helping_hands repo's own AGENT.md guides work on helping_hands itself.

## Self-improving guidance (AGENT.md)

AGENT.md is a living file that agents are instructed to update. As a hand works, it records:

- Code style and formatting preferences
- Design decisions (e.g. "use dataclasses for config")
- Recurring decisions so they aren't re-debated

So the next session—and the next hand—starts with that context. The helping_hands repo has an `AGENT.md` in its root with the exact sections and update rules (outside this vault).

## Project Log

Progress notes live under **Project Log** and can be edited by **users** or **hands**. Each week has a note (e.g. [[Project Log/2026-W08]]). Entries are tagged by author: human or hand, with optional short context. That gives a shared, auditable log of what was done and who contributed. See [[Project Log/Weekly progress]] for the format.
