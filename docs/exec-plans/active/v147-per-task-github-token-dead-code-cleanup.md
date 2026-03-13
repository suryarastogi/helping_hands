## v147 — Per-task GitHub token override, pr_description dead code cleanup, constant docstrings

**Status:** Active
**Created:** 2026-03-13

## Goal

Three self-contained improvements:

1. **Per-task GitHub token override** — Addresses TODO.md item: "ability to add a github token for a specific task." Add `github_token` field to `Config`, wire through `Config.from_env()` via `HELPING_HANDS_GITHUB_TOKEN` env var, pass to `GitHubClient()` in all 3 call sites (`base.py`, `e2e.py`, `cli/base.py`), add `--github-token` CLI arg, add `github_token` field to server `BuildRequest`/`ScheduleRequest` models and Celery task signature.

2. **Remove dead `if cmd else "cli"` fallbacks** in `pr_description.py` — `generate_pr_description()` (line 333) and `generate_commit_message()` (line 635) both have `cli_label = cmd[0] if cmd else "cli"` where `cmd` cannot be None (guarded by early returns on lines 311 and 616). Simplify to `cmd[0]`.

3. **Add docstrings for `_COMMIT_MSG_DIFF_LIMIT` and `_COMMIT_MSG_TIMEOUT`** — These two constants in `pr_description.py` (lines 383-384) lack docstrings, unlike all other module-level constants in the same file which have docstring annotations.

## Tasks

- [x] Add `github_token: str = ""` field to `Config` dataclass
- [x] Load `HELPING_HANDS_GITHUB_TOKEN` env var in `Config.from_env()`
- [x] Pass `config.github_token` (when non-empty) to `GitHubClient()` in `base.py`, `e2e.py`, `cli/base.py`
- [x] Add `--github-token` CLI arg in `cli/main.py` and wire to Config overrides
- [x] Add `github_token` field to `BuildRequest` and `ScheduleRequest` in `server/app.py`
- [x] Add `github_token` parameter to `build_feature()` in `server/celery_app.py` and pass to Config
- [x] Wire `github_token` through server task dispatch (`schedules.py`, `app.py`)
- [x] Remove dead `if cmd else "cli"` in `generate_pr_description()` and `generate_commit_message()`
- [x] Add docstrings for `_COMMIT_MSG_DIFF_LIMIT` and `_COMMIT_MSG_TIMEOUT`
- [x] Add tests for Config `github_token` (7 tests: default, override, env var, override beats env, none preserves env, no env no override, frozen)
- [x] Add tests for `GitHubClient` token passthrough from Config (4 tests: field exists, hand base reads, empty falls back, default empty)
- [x] Add tests for CLI `--github-token` arg (4 tests: parser accepts, default None, wired to config e2e, wired to config backend)
- [x] Add tests for dead code removal and constant docstrings (8 tests: 2 cli_label, 6 constant tests)
- [x] Run lint and tests — 3563 passing, 80 skipped
- [x] Update docs (TODO.md, PLANS.md, QUALITY_SCORE.md, Week-12)

## Completion criteria

- All new tests pass
- `ruff check` and `ruff format` pass
- Per-task GitHub token flows from CLI/server → Config → GitHubClient
- Docs updated with v147 notes
