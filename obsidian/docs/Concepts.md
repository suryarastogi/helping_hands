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

## E2E hand semantics (current implementation)

`E2EHand` is the concrete backend currently used for live clone/edit/commit/push/PR flows. Important behaviors:

- Supports **new PR** and **resume existing PR** (`pr_number`) paths.
- Uses deterministic workspace layout: `{hand_uuid}/git/{repo}`.
- In live mode, updates both:
  - PR description/body (latest timestamp, prompt, commit)
  - Marker-tagged status comment (`<!-- helping_hands:e2e-status -->`)
- In dry-run mode, it performs local clone/edit only and skips commit/push/PR side effects.

This means a rerun updates the same PR state instead of creating drift between old body text and new comments.

## Basic hand semantics (current implementation)

`BasicLangGraphHand` and `BasicAtomicHand` run iterative repo-aware loops with:

- streamed per-iteration output
- cooperative interruption
- iteration-1 bootstrap context from `README.md`/`AGENT.md` (when present) and a bounded repo tree snapshot
- file reads via `@@READ: ...` and read-result feedback blocks
- inline file edits via `@@FILE: ...` fenced full-content blocks
- default final commit/push/PR step

Final PR behavior is enabled by default and can be disabled explicitly (`--no-pr`).
When enabled, push is token-authenticated and non-interactive to avoid OS credential popups.

Implementation note: hand code is now organized as a package module under
`src/helping_hands/lib/hands/v1/hand/`, and iterative file operations route
through shared system helpers in
`src/helping_hands/lib/meta/tools/filesystem.py`.

## CLI backend semantics (current implementation)

CLI-driven backends (`codexcli`, `claudecodecli`) run in two phases:

1. Initialization/learning pass over repo context (`README.md`, `AGENT.md`,
   indexed tree/file snapshot).
2. Task execution pass that applies requested changes directly.

For `claudecodecli`, non-interactive runs default to
`--dangerously-skip-permissions` and now include one automatic follow-up apply
pass for edit-intent prompts when the first task pass produces no git changes.

## Provider wrappers and model resolution

Model/provider behavior now routes through shared provider abstractions:

- `src/helping_hands/lib/ai_providers/` exposes wrapper modules for `openai`, `anthropic`, `google`, and `litellm`.
- Hands resolve model input via `src/helping_hands/lib/hands/v1/hand/model_provider.py`.
  - Supports bare model names (e.g. `gpt-5.2`).
  - Supports explicit `provider/model` forms (e.g. `anthropic/claude-3-5-sonnet-latest`).
- The resolver adapts provider wrappers to backend-specific model/client interfaces (LangGraph and Atomic).

## CI race-condition guard

E2E integration testing is opt-in and environment-gated. In CI matrix runs:

- only `master` + Python `3.13` performs live push/update
- all other matrix entries run dry-run

This avoids concurrent matrix jobs racing on the same PR head branch.

## Type-checking baseline

The repo now uses `ty` as part of pre-commit alongside Ruff. Current baseline intentionally scopes type checks to `src` and ignores two noisy rule classes tied to optional backend imports / protocol mismatch noise:

- `unresolved-import`
- `invalid-method-override`

This keeps type checks actionable while optional-backend implementation is still in scaffold state.

## App-mode monitoring semantics

App mode has two monitoring paths:

- **JSON polling**: `/tasks/{task_id}` is used by the JS-enabled UI and API clients.
- **No-JS fallback**: `/monitor/{task_id}` is a server-rendered HTML page with
  meta refresh, used when client-side JS is blocked or unavailable.
- **Stable monitor layout**: monitor task/status/update/payload cards use fixed
  dimensions so polling updates do not shift page layout; long text scrolls
  inside each card.

In logs, either repeated `/tasks/...` or repeated `/monitor/...` requests are
valid indicators that monitoring is active.

## Repo input behavior

In CLI mode, non-E2E runs accept:

- local repo paths
- GitHub `owner/repo` references (auto-cloned to a temporary workspace)

## Project Log

Progress notes live under **Project Log** and can be edited by **users** or **hands**. Each week has a note (e.g. [[Project Log/2026-W08]]). Entries are tagged by author: human or hand, with optional short context. That gives a shared, auditable log of what was done and who contributed. See [[Project Log/Weekly progress]] for the format.
