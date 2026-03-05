# Reliability

Error handling, retry strategies, and fault tolerance in helping_hands.

## Error handling patterns

### CLI hand subprocess failures

CLI-backed hands handle several failure modes:

1. **Command not found** — `claudecodecli` falls back to `npx` if `claude`
   is missing. Other backends fail with a clear error.
2. **Permission rejection** — If Claude rejects `--dangerously-skip-permissions`
   under root, the backend retries without the flag.
3. **Model unavailable** — `geminicli` retries once without `--model` when
   Gemini rejects a deprecated model.
4. **Idle timeout** — All CLI backends terminate after
   `HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS` (default 900s) of no output.
5. **No edits applied** — `claudecodecli` runs a follow-up enforcement pass
   for edit-intent prompts that produce only prose.

### Iterative hand failures

Iterative hands (`BasicLangGraphHand`, `BasicAtomicHand`, `IterativeHand`)
handle several failure modes:

1. **Provider API failures** — transient API errors (rate limits, server errors)
   surface as exceptions from the AI provider layer. The iteration loop does
   not retry automatically; the hand raises the error to the caller.
2. **Context exhaustion** — long conversations can exceed the model's context
   window. The iteration loop is bounded by `--max-iterations` to prevent
   unbounded growth.
3. **@@READ / @@FILE parse errors** — malformed file operation blocks are
   silently skipped rather than crashing the iteration. Invalid paths are
   rejected by `resolve_repo_target()`.
4. **@@TOOL dispatch failures** — tool invocation errors (bad payload, missing
   dependencies) are captured as `CommandResult` with non-zero exit codes
   and fed back to the model as tool output.
5. **Early completion** — `SATISFIED: yes` signals the model is done, allowing
   the loop to exit before `max_iterations`.
6. **Streaming errors** — surfaced incrementally as they occur, not swallowed

### Finalization failures

- Pre-commit failures trigger auto-fix + one validation retry
- Push failures surface the git error message
- PR creation failures do not affect the local branch state

## Heartbeat monitoring

CLI subprocess runs emit heartbeat lines every
`HELPING_HANDS_CLI_HEARTBEAT_SECONDS` (default 20s) showing elapsed time
and timeout status. This prevents monitoring systems from treating quiet
runs as stalled.

## Task status tracking

- Celery tasks expose status via `/tasks/{task_id}`
- Active task discovery via `/tasks/current` (Flower API + Celery inspect fallback)
- HTML monitor at `/monitor/{task_id}` auto-refreshes without client JS

## Test-level error handling patterns

### Testing pure helpers in isolation

Pure functions (`_infer_provider_name`, `_normalize_args`, `normalize_relative_path`)
are tested directly without mocking. This catches regressions in input validation
and edge cases (empty strings, case sensitivity, type mismatches).

### Dataclass invariants

Frozen dataclasses (`CommandResult`, `HandModel`, `Config`) are tested for
immutability (`pytest.raises(AttributeError)`) and property correctness
(`CommandResult.success` combining exit code and timeout).

### Subprocess mocking

Tests for `run_python_code` and `run_python_script` mock `_resolve_python_command`
to use `sys.executable`, avoiding version-specific Python availability issues in CI.
Inline bash scripts use real subprocess execution since `bash` is always available.

### Security boundary tests

Path traversal tests in `test_filesystem.py` and `test_meta_tools_command.py`
verify that `resolve_repo_target` rejects `../` escapes, absolute paths, and
empty inputs. These are critical for the tool isolation guarantee.

## Idempotency

- E2E PR updates are idempotent: re-running updates the same branch, PR body,
  and status comment instead of creating duplicates
- Worker tasks use Celery task IDs as hand UUIDs for deterministic workspace paths
