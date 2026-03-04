# Product Sense

## What helping_hands solves

Developers spend significant time on repetitive code changes — adding features from specs, fixing bugs from issue descriptions, updating docs. helping_hands automates these by pointing an AI at a repo with a task description and letting it make the changes.

## Target users

1. **Solo developers** — use the CLI to automate tedious tasks locally
2. **Teams** — use the server mode to queue and track builds, with PR-based review
3. **CI/CD pipelines** — use the MCP server or API to integrate AI-driven changes into workflows

## Product principles

- **Low barrier to entry** — `helping-hands owner/repo --prompt "add X"` should work with zero config
- **Non-destructive by default** — changes go through PRs unless explicitly told otherwise
- **Backend-agnostic** — users pick their preferred AI tool (Claude, Codex, Gemini, etc.)
- **Observable** — streaming output, task tracking, and run logs make it clear what the AI is doing

## What we don't do

- We don't replace code review — we create PRs for humans to review
- We don't manage deployments — we stop at the PR/commit boundary
- We don't lock users into a provider — the Hand abstraction keeps backends swappable

## Feature prioritization

When deciding what to build next, weight by:

1. **Reliability** — Does it make existing flows more reliable? (highest priority)
2. **Coverage** — Does it support more repos/languages/workflows?
3. **Speed** — Does it make runs faster or reduce iteration cycles?
4. **Polish** — Does it improve the developer experience?
