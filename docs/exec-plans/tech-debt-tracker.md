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
| Dead code in Atomic `stream()` | Low | `iterative.py` | Lines 830, 858: `delta = current` else branches unreachable because `stream_text` is always `""` at those points |
| Codex `_auto_sandbox_mode` dead code | Low | `codex.py` | Line 62: always returns truthy, making the else branch dead |
| Frontend localStorage polyfill | Low | Frontend | jsdom doesn't fully implement `Storage.clear()`; polyfill in `test/setup.ts` |

## Resolved items

_Move items here when resolved, with date and resolution note._
