# Architecture

High-level view of how helping_hands is built. For file layout and config, see the repo README.

## Modes

The tool supports two ways to run:

- **CLI mode** — Single process in the terminal. User runs `helping_hands <repo>`, gets streaming responses and proposed edits. No server, no persistence.
- **App mode** — A long-running service for async and scheduled work. Not yet implemented; the intended shape is described below.

### App mode (planned)

App mode runs:

1. **Fast server** — A lightweight HTTP/WS server that accepts requests (e.g. "build feature X in repo Y"). It enqueues work instead of doing it inline.
2. **Worker stack** — **Celery** workers consume the queue. **Redis** is the broker (and optionally result backend). **Postgres** holds job metadata, results, and any app state (users, repos, history).
3. **Async jobs** — Each "build this feature" or "ingest this repo" is a task. Users get a job ID and can poll or subscribe for completion; the hand runs in a worker.
4. **Cron / scheduled jobs** — Celery Beat (or similar) runs on a schedule so recurring tasks (e.g. "re-index repo Z daily" or "weekly summary") happen without user action.

So: same core (Repo + Agent) in both modes; CLI calls it directly, app mode wraps it in tasks and runs it in workers. Config (model, paths) is shared; app mode adds server/Redis/Postgres settings.

## Layers (shared)

1. **CLI / Server** — Entry point. CLI parses args and runs the loop; in app mode, the server receives requests and enqueues tasks.
2. **Repo** — Clones or opens a git repo, walks the tree, builds an index. Output is structured context for the hand.
3. **Agent** — The "hand." Receives repo context + user messages, calls the AI, streams responses, and proposes edits. Same in both modes; in app mode it runs inside a worker.
4. **Config** — Single place for settings. No global state; config is passed through.

## Data flow (CLI)

```
User → CLI → Config
         → Repo → context
         → Agent(context, messages) → AI → streamed response / proposed edits
         → (optional) write back to AGENT.md or project log
```

## Data flow (app mode, planned)

```
User/Client → Fast server → enqueue task (Redis)
                Celery worker ← task
                → Repo → context → Agent → AI → result
                → store result / state (Postgres)
Cron (Celery Beat) → enqueue scheduled tasks → same worker path
```

## Design principles

- **Plain data between layers** — Dicts or dataclasses, not tight coupling. Easier to test and swap implementations.
- **Streaming by default** — AI output streams to the terminal; no "wait for full response" unless needed.
- **Explicit config** — No module-level singletons. Config is loaded once and passed in.

These are also reflected in the repo's [[AGENT.md]] under Design preferences.
