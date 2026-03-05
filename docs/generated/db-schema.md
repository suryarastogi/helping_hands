# Database Schema Reference

> Auto-generated schema documentation for helping_hands data models.

## Server Data Models

### ScheduledTask

Defined in `src/helping_hands/server/schedules.py`. Persisted as JSON in Redis under
`helping_hands:schedule:meta:<schedule_id>`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `schedule_id` | `str` | — | Unique identifier (`sched_` + 12 hex chars) |
| `name` | `str` | — | Human-readable schedule name |
| `cron_expression` | `str` | — | Standard 5-field cron expression |
| `repo_path` | `str` | — | Repository path or `owner/repo` |
| `prompt` | `str` | — | AI task prompt |
| `backend` | `str` | `"claudecodecli"` | Hand backend identifier |
| `model` | `str \| None` | `None` | AI model override |
| `max_iterations` | `int` | `6` | Max iteration count |
| `pr_number` | `int \| None` | `None` | Target PR number |
| `no_pr` | `bool` | `False` | Skip PR creation |
| `enable_execution` | `bool` | `False` | Allow command execution |
| `enable_web` | `bool` | `False` | Allow web access |
| `use_native_cli_auth` | `bool` | `False` | Use native CLI auth |
| `fix_ci` | `bool` | `False` | Auto-fix CI failures |
| `ci_check_wait_minutes` | `float` | `3.0` | CI check wait timeout |
| `tools` | `list[str]` | `[]` | Enabled tool names |
| `skills` | `list[str]` | `[]` | Enabled skill names |
| `enabled` | `bool` | `True` | Whether schedule is active |
| `created_at` | `str` | auto (ISO 8601) | Creation timestamp |
| `last_run_at` | `str \| None` | `None` | Last execution timestamp |
| `last_run_task_id` | `str \| None` | `None` | Last Celery task ID |
| `run_count` | `int` | `0` | Total execution count |

### TaskResult Normalization

Defined in `src/helping_hands/server/task_result.py`. Not persisted directly — used to
normalize Celery task results for API responses.

| Input Type | Output Format |
|-----------|---------------|
| `None` | `None` |
| `dict` | Passthrough |
| `BaseException` | `{"error": str, "error_type": str, "status": str}` |
| Other | `{"value": str, "value_type": str, "status": str}` |

## RepoIndex

Defined in `src/helping_hands/lib/repo.py`. In-memory only (not persisted).

| Field | Type | Description |
|-------|------|-------------|
| `root` | `Path` | Absolute path to repository root |
| `files` | `list[str]` | Sorted relative file paths (excludes `.git/`) |

## Configuration (Config)

Defined in `src/helping_hands/lib/config.py`. Loaded from environment variables and
CLI arguments. Not persisted — constructed per invocation.

## Redis Key Patterns

| Pattern | Purpose |
|---------|---------|
| `helping_hands:schedule:meta:<id>` | Schedule metadata JSON |
| `redbeat:helping_hands:scheduled:<id>` | RedBeat scheduler entry |
| `celery-task-meta-<task_id>` | Celery task result (standard) |
