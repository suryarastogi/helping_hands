# Plans

Index of execution plans for helping_hands development.

## Active plans

_No active plans._

## Completed plans

- [Docs and Testing v9](exec-plans/completed/docs-and-testing-v9.md) —
  Bootstrap and inline edit tests (_build_tree_snapshot, _read_bootstrap_doc, _build_bootstrap_context, _apply_inline_edits); QUALITY_SCORE.md updates (completed 2026-03-05)


- [Docs and Testing v8](exec-plans/completed/docs-and-testing-v8.md) —
  Format helper tests (CommandResult, WebSearchResult, WebBrowseResult), tool config helpers, base.py static helpers (_default_base_branch, _build_generic_pr_body); QUALITY_SCORE.md updates (completed 2026-03-05)

- [Docs and Testing v7](exec-plans/completed/docs-and-testing-v7.md) —
  Dedicated test suites for Claude, Codex, Gemini, OpenCode CLI hands (106 tests); DESIGN.md CLI backend patterns (completed 2026-03-05)
- [Docs and Testing v6](exec-plans/completed/docs-and-testing-v6.md) —
  CLI hand helpers, web tool internals, registry validators test coverage; SECURITY.md & RELIABILITY.md iterative hand docs (completed 2026-03-05)
- [Docs and Testing v5](exec-plans/completed/docs-and-testing-v5.md) —
  Pure helper test coverage (model_provider, command, config, filesystem), QUALITY_SCORE.md & RELIABILITY.md enhancements (completed 2026-03-05)
- [Docs and Testing v4](exec-plans/completed/docs-and-testing-v4.md) —
  AI provider & CLI hand test expansion, two-phase CLI hands design doc, SECURITY.md sandboxing (completed 2026-03-04)
- [Docs and Testing v3](exec-plans/completed/docs-and-testing-v3.md) —
  Iterative hand tests, ARCHITECTURE.md data flows, FRONTEND.md expansion (completed 2026-03-04)
- [Docs and Testing v2](exec-plans/completed/docs-and-testing-v2.md) —
  Fill documentation gaps and add targeted tests for untested modules (completed 2026-03-04)
- [Improve Docs and Testing](exec-plans/completed/improve-docs-and-testing.md) —
  Established docs structure, filled initial testing gaps (completed 2026-03-04)

## How plans work

1. Plans are created in `docs/exec-plans/active/` with a descriptive filename
2. Each plan has a status, creation date, tasks, and completion criteria
3. When all tasks are done, the plan moves to `docs/exec-plans/completed/`
4. The tech debt tracker (`docs/exec-plans/tech-debt-tracker.md`) captures
   ongoing technical debt items that don't warrant a full plan
