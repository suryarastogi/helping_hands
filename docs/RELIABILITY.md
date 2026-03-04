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

- Iteration loops are bounded by `--max-iterations`
- `SATISFIED: yes` signals early completion
- Streaming errors are surfaced incrementally, not swallowed

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

## Idempotency

- E2E PR updates are idempotent: re-running updates the same branch, PR body,
  and status comment instead of creating duplicates
- Worker tasks use Celery task IDs as hand UUIDs for deterministic workspace paths
