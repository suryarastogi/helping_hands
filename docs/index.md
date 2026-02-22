# helping_hands

**AI-powered repo builder** — point it at a codebase, describe what you want, and let an AI agent help you build and ship features.

For full project details, see the [README](https://github.com/suryarastogi/helping_hands#readme).

## API Reference

Browse the auto-generated docs from source:

- **lib** — Core library: [config](api/lib/config.md), [repo](api/lib/repo.md), [github](api/lib/github.md), [hands v1](api/lib/hands/v1/hand.md)
- **cli** — CLI entry point: [main](api/cli/main.md)
- **server** — App mode: [app](api/server/app.md), [celery_app](api/server/celery_app.md)

## Runtime flow

- Server mode: server enqueues a hand task, then the hand executes.
- CLI mode: CLI invokes the hand directly (index-only, E2E mode, or iterative basic backends).
- `E2EHand` is the minimal concrete hand used to validate the full
  clone/edit/commit/push/PR lifecycle.
- Optional `pr_number` lets the hand resume/update an existing PR branch.
- Basic iterative backends (`basic-langgraph`, `basic-atomic`, `basic-agent`)
  stream multi-step output and, by default, attempt a final commit/push/PR step
  unless disabled via `--no-pr`.
