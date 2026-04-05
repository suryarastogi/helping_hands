# CLI Introspection & Self-Service UX

How the CLI helps users discover capabilities, diagnose problems, and get
started without reading source code.

## Context

As helping_hands gained more backends, tool categories, and configuration
options, new users needed ways to answer "what can this tool do?" and "why
isn't it working?" without digging through source code or docs. Between
v344 and v375 a set of self-service CLI features was added to address this.

## Features

### `--version` / `-V` (v365)

Prints `helping-hands {version}` and exits. Intercepted in `main()` before
`argparse.parse_args()` so it works without a positional `repo` argument.

```
$ helping-hands --version
helping-hands 0.1.0
```

### `helping-hands doctor` (v344, v347, v348)

Diagnostic command that checks prerequisites and reports actionable errors.

**Checks performed:**
- Python version (3.12+ required)
- `git` availability
- `uv` availability
- AI provider API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`)
- `GITHUB_TOKEN` / `GH_TOKEN` presence
- Optional CLI backends (`claude`, `codex`, `goose`, `gemini`, `opencode`, `devin`)
- Optional Python extras (`langchain`, `atomic`)
- Docker CLI availability (for `docker-sandbox-*` backends)
- Node.js version (v18+ for frontend development)
- `redis-cli` availability (for local-stack server mode)
- `docker compose` subcommand (for app-mode deployment)

Exit code 0 when all required checks pass; exit code 1 with messages for
each failure.

**Design decisions:**
- Each check is a private `_check_*()` function returning a `CheckResult`
  dataclass with `name`, `status` (pass/warn/fail), and `message`.
- `collect_checks()` gathers all results; `format_results()` renders them.
- Subprocess checks use `shutil.which()` for binary detection and
  `subprocess.run()` with short timeouts for version extraction.
- Doctor runs as a subcommand (`helping-hands doctor`), not a flag, because
  it produces multi-line diagnostic output rather than a single value.

### `--list-backends` (v370, v371, v375)

Prints a table of all supported backends with availability, enabled status,
and description.

```
$ helping-hands --list-backends
Backend              Status   Enabled  Description
basic-langgraph      [+]      [+]      LangGraph agent loop ...
claude               [+]      [+]      Claude Code CLI ...
codex                [-]      [+]      OpenAI Codex CLI ...
...
```

**Design decisions:**
- Availability is checked via `shutil.which()` for CLI backends and
  `__import__()` for library backends (`_check_backend_available()`).
- Enabled status reads `*_ENABLED` env vars via `is_backend_enabled()`.
- Descriptions come from `BACKEND_DESCRIPTIONS` dict in `factory.py` with
  a module-level consistency check against `SUPPORTED_BACKENDS`.
- Intercepted before argparse like `--version`.

### `--list-tools` (v372)

Prints a table of tool categories with their tool spec names.

```
$ helping-hands --list-tools
Category      Tools
execution     run_python_code, run_python_script, run_bash_script
web           web_search, browse_url
```

**Design decisions:**
- Uses `available_tool_category_names()` from the registry module.
- Complements `--list-backends` for full capability discovery.

### Interactive mode (v349)

When `--prompt` is omitted, reads the task from stdin.

- **TTY mode:** prints a prompt message to stderr, reads until Ctrl+D.
- **Pipe mode:** reads silently (`echo "task" | helping-hands .`).
- Empty input or Ctrl+C exits cleanly with an error message.

**Design decisions:**
- `read_prompt_from_stdin()` is a standalone function for testability.
- Prompt message goes to stderr so it doesn't contaminate piped output.
- `--prompt` default changed from `DEFAULT_SMOKE_TEST_PROMPT` to `None`
  to distinguish "not provided" from "explicitly set".

### First-run welcome banner (v346)

On the very first CLI invocation, prints a welcome message with pointers
to the quick-start guide, `doctor` command, and examples directory.

**Design decisions:**
- Tracked via `~/.helping_hands/.first_run_done` marker file.
- `_maybe_show_first_run_banner()` returns `True` if the banner was shown
  (useful for testing).
- Banner prints to stderr to avoid contaminating piped output.

## Interception order

All self-service flags are handled in `main()` before `argparse.parse_args()`
to avoid requiring the positional `repo` argument:

1. First-run banner check
2. `doctor` subcommand
3. `--version` / `-V`
4. `--list-backends`
5. `--list-tools`
6. Normal argument parsing

## Alternatives considered

- **Subcommands for everything** (e.g. `helping-hands list-backends`):
  Rejected because argparse subcommands conflict with the positional `repo`
  argument. Flags are simpler and consistent with standard CLI conventions.
- **Combined `--list` flag** with a type argument: Rejected for simplicity;
  separate flags are more discoverable and easier to document.

## Consequences

- Users can evaluate available backends without reading factory.py.
- `doctor` gives actionable setup guidance, reducing support burden.
- Interactive mode lowers the barrier to first use.
- Pre-argparse interception means these flags bypass all validation,
  which is intentional — they should always work regardless of other config.
