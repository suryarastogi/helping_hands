# helping_hands

**AI-powered repo builder** — point it at a codebase, describe what you want, and let an AI agent help you build and ship features.

For full project details, quick start, configuration, backend requirements, and
CLI examples, see the [README](https://github.com/suryarastogi/helping_hands#readme).

## API Reference

Browse the auto-generated docs from source:

- **lib** — Core library: [config](api/lib/config.md), [repo](api/lib/repo.md), [github](api/lib/github.md), [ai providers](api/lib/ai_providers.md) ([openai](api/lib/ai_providers/openai.md), [anthropic](api/lib/ai_providers/anthropic.md), [google](api/lib/ai_providers/google.md), [ollama](api/lib/ai_providers/ollama.md), [litellm](api/lib/ai_providers/litellm.md), [types](api/lib/ai_providers/types.md)), [hands v1](api/lib/hands/v1/hand.md), [meta tools](api/lib/meta/tools.md) ([filesystem](api/lib/meta/tools/filesystem.md), [command](api/lib/meta/tools/command.md), [web](api/lib/meta/tools/web.md))
- **cli** — CLI entry point: [main](api/cli/main.md)
- **server** — App mode: [app](api/server/app.md), [celery_app](api/server/celery_app.md), [schedules](api/server/schedules.md), [task_result](api/server/task_result.md), [mcp_server](api/server/mcp_server.md)
