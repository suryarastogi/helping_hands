# Tech Debt Tracker

Ongoing technical debt items that don't warrant a full execution plan.

## Active items

| Item | Priority | Module | Notes |
|---|---|---|---|
| Type checker not in CI | Medium | CI | ty lacks stable CI runner; add when available |
| Claude CLI scaffold placeholder | Low | `cli/claude.py` | Replace with real subprocess integration |
| Gemini CLI scaffold placeholder | Low | `cli/gemini.py` | Replace with real subprocess integration |
| Backend routing incomplete | Medium | CLI | Extend to remaining non-basic hands |
| Streaming for scaffold CLI hands | Low | CLI hands | Replace single-chunk with real streaming |
| E2E hardening | Medium | `e2e.py` | Branch collision, draft PR, idempotency |

## Resolved items

_Move items here when resolved, with date and resolution note._
