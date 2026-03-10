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
| Frontend localStorage polyfill | Low | Frontend | jsdom doesn't fully implement `Storage.clear()`; polyfill in `test/setup.ts` |
| `if __name__ == "__main__"` guard | None | `cli/main.py` | Line 367: standard script entry point guard; inherently untestable via pytest (not actual dead code) |
| CLI IO loop heartbeat-without-timeout branch | Low | `cli/base.py` | Branch 552->559: heartbeat fires but idle timeout hasn't been reached; requires real async subprocess timing to trigger both branches in a single invocation |
| `_decode_bytes` latin-1 fallback | None | `web.py` | latin-1 accepts all byte values; fallback marked `pragma: no cover` as defensive-only |
| `if __name__ == "__main__"` guard (MCP) | None | `mcp_server.py` | Line 393: standard script entry point guard; inherently untestable via pytest (not actual dead code) |

## Resolved items

| Item | Resolved | Notes |
|---|---|---|
| Dead code in Atomic `stream()` | 2026-03-10 | Removed unreachable `else: delta = current` branches in `iterative.py` (v104) |
| Codex `_auto_sandbox_mode` dead code | 2026-03-10 | Removed redundant `if not sandbox_mode` guard in `codex.py` (v104) |
| Goose `_GOOSE_DEFAULT_MODEL` fallback dead code | 2026-03-10 | Removed unreachable `if not model` fallback in `goose.py` (v104) |
| E2E `final_pr_number is None` dead code | 2026-03-10 | Removed always-true `is not None` guard in `e2e.py` (v104) |
