# Tech debt tracker

Track technical debt and improvement opportunities.

## Active debt

| Item | Severity | Module | Notes |
|---|---|---|---|
| CodexCLI hand is scaffold only | Medium | `hands/v1/hand.py` | Needs subprocess implementation |
| GeminiCLI hand is scaffold only | Medium | `hands/v1/hand.py` | Needs subprocess implementation |
| No streaming for CLI hands | Medium | `hands/v1/hand.py` | Incremental output not implemented |
| `ty` not in CI | Low | `.github/workflows/ci.yml` | Waiting for stable CI runner |
| No integration tests | Medium | `tests/` | All tests mock external deps |
| App mode server not fully wired | Low | `server/` | build_feature returns greeting, not AI output |

## Resolved

| Item | Resolved date | Resolution |
|---|---|---|
| No backend selection | 2026-03-14 | Added `--backend` flag and `Config.backend` |
| ClaudeCode hand is scaffold only | 2026-03-14 | Implemented subprocess execution |
