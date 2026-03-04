# Execution Plans

## Purpose

Execution plans track multi-session work that spans beyond a single AI-driven run. They provide continuity — when a new session starts, it can pick up where the last one left off by reading the active plan.

## Directory Structure

```
docs/exec-plans/
├── active/              # Currently in-progress plans (0-2 at a time)
│   └── <plan-name>.md
├── completed/           # Finished plans (kept for reference)
│   └── <plan-name>.md
└── tech-debt-tracker.md # Running list of known technical debt
```

## Plan Lifecycle

1. **Create** — When starting a multi-step improvement, create a plan in `active/` with phases and checkboxes.
2. **Execute** — Each session reads the active plan, picks the next unchecked item, implements it, and checks it off.
3. **Complete** — When all items are checked, move the plan from `active/` to `completed/`.

## Plan Format

```markdown
# Execution Plan: <Title>

**Status:** Active | Completed
**Created:** YYYY-MM-DD
**Completed:** YYYY-MM-DD (when done)
**Goal:** One-sentence description of what this plan achieves.

---

## Phase 1: <Name>

- [ ] Task description
- [ ] Task description

## Phase 2: <Name>

- [ ] Task description

---

## Completion Criteria

What must be true for this plan to move to completed/.
```

## Guidelines

- Keep plans small and scoped (3-4 phases, 15-20 tasks max)
- Each task should be completable in a single session
- Phase boundaries mark safe stopping points
- Update the tech-debt-tracker when you discover debt during execution
