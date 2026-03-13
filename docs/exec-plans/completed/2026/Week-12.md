# Week 12 (Mar 13 – Mar 19, 2026)

Per-task GitHub token override, dead code cleanup, and constant docstrings.

---

## Mar 13 — Per-task GitHub token, dead code cleanup, constant docstrings (v147)

Added `github_token: str = ""` field to `Config` dataclass with `HELPING_HANDS_GITHUB_TOKEN` env var support in `Config.from_env()`. Wired `config.github_token` to `GitHubClient(token=...)` in all 3 call sites (`base.py`, `e2e.py`, `cli/base.py`). Added `--github-token` CLI argument in `cli/main.py` that overrides the env var, passed through Config overrides for both E2E and backend code paths. Added `github_token` field to server `BuildRequest` and `ScheduleRequest` models in `app.py`, wired through Celery `build_feature()` task parameter, and propagated via `ScheduledTask` in `schedules.py`. Removed dead `if cmd else "cli"` fallbacks in `generate_pr_description()` (line 333) and `generate_commit_message()` (line 635) in `pr_description.py` — `cmd` cannot be None at those points due to early returns. Added docstrings for `_COMMIT_MSG_DIFF_LIMIT` and `_COMMIT_MSG_TIMEOUT` constants in `pr_description.py`. **3563 passing tests (+21 new: 7 Config, 4 Hand passthrough, 4 CLI arg, 2 cli_label, 6 constant tests), 80 skipped.**

---

**Week summary:** Feature addition (per-task GitHub token override) flowing from CLI/server through Config to GitHubClient, plus dead code cleanup and constant docstring consistency. Grew from 3542 to 3563 backend tests.
