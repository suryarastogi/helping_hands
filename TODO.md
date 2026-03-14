# Project todos

## Open items

  - [x] commit message created by claudecodecli still mediocore *(Fixed in v136: `_is_trivial_message()` rejects `feat: -`, `feat: ...` etc. Further improved in v146: `_infer_commit_type()` smart type inference and `_truncate_text()` truncation indicators.)*

- [x] per task github token override -- ability to add a github token for a specific task, so that it can be used for that task instead of the default token. This would be useful for tasks that require different permissions than the default token. Also useful if no default token is set, but you want to use a token for a specific task. *(Implemented in v147: `Config.github_token` field, `HELPING_HANDS_GITHUB_TOKEN` env var, `--github-token` CLI arg, server `BuildRequest`/`ScheduleRequest` fields, Celery task parameter, wired to `GitHubClient` in all 3 call sites.)*

- [x] kill signal from UI for a task -- ability to send a kill signal from the UI to stop a task that is currently running. This would be useful for tasks that are taking too long or are no longer needed. *(Implemented in v160: `POST /tasks/{task_id}/cancel` endpoint using Celery `revoke(terminate=True, signal="SIGTERM")`, cancel button in both inline HTML monitor and React frontend, 15 new tests.)*

- [x] checkout additional repos as read-only for reference (read-only dir) -- ability to checkout additional repos as read-only for reference during task execution. This would be useful for tasks that require access to multiple repos, but only need read-only access to some of them. *(Implemented: `Config.reference_repos` field, `HELPING_HANDS_REFERENCE_REPOS` env var, `--reference-repos` CLI arg, `RepoIndex.reference_repos` for passing to hands, server `BuildRequest`/`ScheduleRequest` fields, Celery task parameter with shallow clone logic, system prompt sections in both Hand base and CLI hands, inline HTML UI and React frontend form fields, `ScheduledTask` persistence. Reference repos are cloned as `--depth 1` shallow clones and surfaced as read-only context in AI agent prompts.)*
