# Tech Debt Tracker

Ongoing technical debt items that don't warrant a full execution plan.

## Active items

| Item | Priority | Module | Notes |
|---|---|---|---|
| Streaming for scaffold CLI hands | Low | CLI hands | Replace single-chunk with real streaming |
| E2E hardening | Low | `e2e.py` | Branch collision, idempotency (draft PR added in v105) |
| `if __name__ == "__main__"` guard | None | `cli/main.py` | Line 367: standard script entry point guard; inherently untestable via pytest (not actual dead code) |
| CLI IO loop heartbeat-without-timeout branch | Low | `cli/base.py` | Branch 552->559: heartbeat fires but idle timeout hasn't been reached; requires real async subprocess timing to trigger both branches in a single invocation |
| `_decode_bytes` latin-1 fallback | None | `web.py` | latin-1 accepts all byte values; fallback marked `pragma: no cover` as defensive-only |
| `if __name__ == "__main__"` guard (MCP) | None | `mcp_server.py` | Line 393: standard script entry point guard; inherently untestable via pytest (not actual dead code) |
| `_commit_message_from_prompt` unreachable branch | None | `pr_description.py` | Branch 581→583: `if not candidate` False path is unreachable — candidate starts as `""` and `break` always fires on first non-boilerplate line (v173) |
| Position throttle timer-clear guard | None | `useMultiplayer.ts` | Lines 522–525: `if (broadcastTimerRef.current)` inside `elapsed >= threshold` branch is unreachable — React's effect cleanup always nullifies the timer before re-invocation. Defensive-only. |
| Cursor throttle timer-clear guard | None | `useMultiplayer.ts` | Lines 740–743: same pattern for cursor throttle — unreachable for the same reason as position throttle. |

## Resolved items

| Item | Resolved | Notes |
|---|---|---|
| Dead code in Atomic `stream()` | 2026-03-10 | Removed unreachable `else: delta = current` branches in `iterative.py` (v104) |
| Codex `_auto_sandbox_mode` dead code | 2026-03-10 | Removed redundant `if not sandbox_mode` guard in `codex.py` (v104) |
| Goose `_GOOSE_DEFAULT_MODEL` fallback dead code | 2026-03-10 | Removed unreachable `if not model` fallback in `goose.py` (v104) |
| E2E `final_pr_number is None` dead code | 2026-03-10 | Removed always-true `is not None` guard in `e2e.py` (v104) |
| Backend routing incomplete | 2026-03-10 | Added `docker-sandbox-claude` to server `_SUPPORTED_BACKENDS`, `_BACKEND_LOOKUP`, `BackendName`, and Celery hand instantiation (v105) |
| E2E draft PR | 2026-03-10 | E2E hand now creates draft PRs by default via `HELPING_HANDS_E2E_DRAFT_PR` env var (v105) |
| Frontend localStorage polyfill | 2026-03-10 | Full polyfill in `test/setup.ts` with getItem/setItem/removeItem/clear/length/key (v105) |
| Claude CLI scaffold placeholder | 2026-03-10 | Claude Code CLI hand is fully implemented with `_StreamJsonEmitter`, async `_invoke_claude`, and complete test coverage (v107) |
| Gemini CLI scaffold placeholder | 2026-03-10 | Gemini CLI hand is fully implemented with model resolution, auth, retry logic, and complete test coverage (v107) |
| Type checker not in CI | 2026-03-10 | Added `ty check` step to CI workflow; fixed 12 type errors in `e2e.py`, `celery_app.py`, `schedules.py`; removed stale `type: ignore` comments (v109) |
