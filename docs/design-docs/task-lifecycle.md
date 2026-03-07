# Task Lifecycle

How server-mode tasks flow from submission through execution to result
retrieval.

## Context

In app mode, the FastAPI server accepts build requests and delegates them to
Celery workers. The task lifecycle spans multiple processes: the web server
enqueues, a worker executes, and the client polls for progress and results.
Understanding this flow is essential for debugging task failures, extending
the progress reporting, and adding new task types.

## Lifecycle phases

### 1. Submission

The client (React frontend or API caller) posts to `/build` with parameters:
repo path, prompt, backend, model, options. The server validates inputs,
normalizes the backend name via `_normalize_backend`, and enqueues a
`build_feature` Celery task. The returned task ID becomes the handle for all
subsequent polling.

### 2. Repo resolution

On the worker, `_resolve_repo_path` determines whether the input is a local
directory or an `owner/repo` reference. Remote repos are shallow-cloned to a
temporary directory. When a `pr_number` is provided, `--no-single-branch` is
used so the PR branch can be fetched and pushed back.

Clone URLs are token-authenticated when `GITHUB_TOKEN` or `GH_TOKEN` is set.
Tokens are redacted from error messages via `_redact_sensitive`.

### 3. Hand instantiation

The worker resolves the runtime backend (e.g., `basic-agent` maps to
`basic-atomic`), builds a `Config` from environment, creates a `RepoIndex`,
and instantiates the appropriate `Hand` subclass. Missing optional
dependencies (langchain, atomic_agents) produce clear install hints.

Auth checks run before instantiation for backends that need them (`codexcli`
requires `OPENAI_API_KEY` or `~/.codex/auth.json`; `geminicli` requires
`GEMINI_API_KEY`).

### 4. Streaming execution

The hand runs via `_collect_stream`, which iterates over `hand.stream(prompt)`
chunks. An `_UpdateCollector` buffers partial lines and flushes them into the
update list:

- Lines are split on `\n` boundaries.
- Partial buffers flush at `_BUFFER_FLUSH_CHARS` (180 chars default, 40 in
  verbose mode).
- Individual lines are truncated at `_MAX_UPDATE_LINE_CHARS` (800/4000).
- The update list is capped at `_MAX_STORED_UPDATES` (200/2000) using FIFO
  trimming.

### 5. Progress reporting

`_update_progress` publishes Celery `PROGRESS` state updates with full task
metadata (backend, model, repo, updates list, etc.). Updates are emitted:

- Once at task start (`stage="starting"`)
- Periodically during streaming (every 8th chunk, or every 2nd in verbose mode)
- Once after stream completion

The client polls `/tasks/{task_id}` and reads the `meta` dict from the
`PROGRESS` state to display live output.

### 6. Result normalization

When the task completes, `build_feature` returns a dict with `status`,
`prompt`, `backend`, `message`, `updates`, and other metadata. For API
consumers, `normalize_task_result` in `server/task_result.py` converts
non-dict results (exceptions, bare values) into JSON-serializable dicts.

### 7. Cleanup

Temporary clone directories are cleaned up in a `finally` block via
`shutil.rmtree`. This runs even if the hand raises, preventing disk
accumulation.

## Scheduled tasks

`scheduled_build` is triggered by RedBeat on a cron schedule. It looks up
the schedule configuration, checks that the schedule is enabled, and enqueues
a `build_feature` task with the saved parameters. The triggered task ID is
recorded via `ScheduleManager.record_run`.

## E2E task variant

`E2EHand` tasks bypass the streaming flow. They call `hand.run()` directly
and return the response message. This is because E2E runs manage their own
clone/branch lifecycle internally.

## Key source files

- `src/helping_hands/server/celery_app.py` — Task definitions and worker helpers
- `src/helping_hands/server/app.py` — FastAPI endpoints and task submission
- `src/helping_hands/server/task_result.py` — Result normalization
- `src/helping_hands/server/schedules.py` — Scheduled task management

## Alternatives considered

- **WebSocket streaming** — Would provide real-time updates without polling,
  but adds infrastructure complexity. Celery PROGRESS state with periodic
  polling is simpler and works well enough for the current UI.
- **Direct async execution** — Running hands directly in FastAPI async
  handlers was considered but would block the event loop and prevent scaling
  to multiple concurrent tasks.

## Consequences

- Task state is stored in Redis (Celery result backend), making it ephemeral.
  Long-term persistence would require writing results to Postgres.
- The `_MAX_STORED_UPDATES` cap means very long tasks lose early output.
  This is acceptable because the full output is in `message`.
- Progress update frequency is a tradeoff between UI responsiveness and
  Redis write load.
