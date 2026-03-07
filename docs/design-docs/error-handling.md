# Error Handling

How helping_hands handles errors across modules without crashing user-facing flows.

## Context

AI-powered code modification involves many failure points: CLI tools may be
missing, API keys may be invalid, subprocess execution may time out, and
remote services may be unavailable. The codebase needs consistent error
handling that keeps the user-facing flow moving rather than failing at the
first obstacle.

## Decision: Fail narrowly, not broadly

Each error recovery boundary is placed at the narrowest scope where the
failure can be contained. A failure in PR description generation should not
prevent the commit. A missing health check dependency should not crash the
server.

## Recovery patterns

### 1. Exception suppression with fallback

**Where:** `_update_pr_description`, `_skip_permissions_enabled`, `_finalize_repo_pr`

Wrap optional enhancements in `try/except`; on failure, silently fall back to
a simpler path instead of crashing the overall operation.

```python
try:
    rich_title, rich_body = generate_pr_description(diff)
except Exception:
    rich_title, rich_body = None, None  # fall back to heuristic
```

**When to use:** The operation is a "nice-to-have" enhancement, and a safe
default exists.

### 2. Retry with modified command

**Where:** `_retry_command_after_failure` (Claude root error, Gemini model-not-found)

On specific CLI errors, re-invoke with a modified command rather than failing
immediately.

- Claude: strip `--dangerously-skip-permissions` when running as root
- Gemini: drop `--model` when the CLI reports model unavailable

**When to use:** The failure is due to a specific, detectable condition that
can be resolved by adjusting the invocation.

### 3. Fallback command

**Where:** `_fallback_command_when_not_found` (Claude `npx` fallback)

When the primary CLI binary is missing (`FileNotFoundError`), try an
alternative command before giving up.

```
claude not found → try npx -y @anthropic-ai/claude-code
```

**When to use:** An alternative installation method exists for the tool.

### 4. Graceful degradation

**Where:** `_discover_catalog` (empty dir), `_check_*_health` probes, `_has_*_auth` checks

Return a safe default (empty dict, `"error"`, `False`) when optional
dependencies or resources are unavailable, rather than raising.

**When to use:** The missing resource is optional and has a well-defined
"absent" state.

### 5. Default branch fallback

**Where:** `_finalize_repo_pr`

When the remote API fails to provide the default branch, fall back to
`_default_base_branch()` (`"main"`) rather than crashing.

**When to use:** The system has a reasonable default when the canonical value
is unavailable.

### 6. Platform capability detection

**Where:** `_skip_permissions_enabled` (`os.geteuid`)

Use `getattr` + `callable` checks before invoking platform-specific APIs;
gracefully degrade on platforms where the API is absent.

```python
geteuid = getattr(os, "geteuid", None)
if callable(geteuid):
    ...
```

**When to use:** Code must run on multiple platforms with different API surfaces.

### 7. Idle timeout with heartbeat

**Where:** CLI IO loop (`_invoke_cli_with_cmd`)

Emit periodic heartbeat messages during long-running subprocesses; terminate
only after a configurable idle threshold, not on first silence.

**When to use:** External processes have variable startup/processing time and
callers need evidence the system is still alive.

### 8. Async fallback chains

**Where:** `BasicAtomicHand.stream()`

Try `async for`, then `await`, then sync `run()` — three progressively simpler
execution paths for agent output that may or may not be async.

**When to use:** The output interface is polymorphic and may be sync, async
iterable, or awaitable depending on the underlying library.

## Anti-patterns

- **Catching `Exception` too broadly** — Only suppress exceptions at boundaries
  where you have a meaningful fallback. Never swallow errors silently in core
  logic.
- **Retry loops without termination** — Always limit retries (one retry for CLI
  command modification). Never retry the same command infinitely.
- **Hiding errors from the user** — Suppressed errors should still be logged or
  emitted as status messages. The user should know when a fallback was used.

## Consequences

- More code paths to test (each recovery pattern creates at least two branches)
- Coverage-guided iteration catches untested error paths via branch coverage
- Dead code from impossible-to-trigger guards is documented rather than tested
  (see `docs/exec-plans/tech-debt-tracker.md`)

## Alternatives considered

- **Let it crash** — Simpler but poor UX for a tool that runs long AI tasks.
  A crash at the PR step wastes the entire AI execution.
- **Global error handler** — Would catch everything but can't provide
  context-specific recovery. A subprocess retry needs different logic than a
  health check fallback.
