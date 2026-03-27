# GitHub Client

Design of the `lib/github.py` module: authentication, repository operations,
and token safety.

## Context

Every hand that creates commits, pushes branches, or opens pull requests flows
through `GitHubClient`. The module wraps [PyGithub](https://github.com/PyGithub/PyGithub)
for the REST API and subprocess `git` for local operations. It was designed to
keep token handling centralized and to prevent accidental leaks in logs or error
messages.

## Authentication

`GitHubClient` resolves a token through a strict fallback chain:

1. Explicit `token=` argument (highest priority)
2. `GITHUB_TOKEN` environment variable
3. `GH_TOKEN` environment variable

If none are set, `__post_init__` raises `ValueError` immediately. There is no
unauthenticated mode -- every operation requires a valid token.

The token is embedded in HTTPS clone/push URLs using the `x-access-token`
scheme (`https://x-access-token:<token>@github.com/owner/repo.git`). This
avoids credential prompts in non-interactive environments (CI, containers,
Celery workers).

## Token safety

All subprocess output and error messages pass through `_redact_sensitive()`
before logging or raising. This regex-based redactor replaces the token portion
of `x-access-token` URLs with `***`, preventing token leaks in:

- Log output from `_run_git()` failures
- CLI/server error messages surfaced to users
- Exception tracebacks

The redaction is applied to both the command string and stderr output of any
failed git subprocess.

## Repository operations

### Clone

`clone()` constructs a token-authenticated HTTPS URL and shells out to
`git clone`. It supports:

- **Shallow clones** (`depth=1` by default) for fast workspace setup
- **Branch selection** for resuming work on an existing branch
- Returns the destination `Path` for downstream use

### Branch management

Static methods operate on local repos without requiring the PyGithub client:

- `create_branch()` -- checkout -b
- `switch_branch()` -- checkout existing
- `fetch_branch()` -- fetch a single remote ref into a local branch
- `pull()` -- pull with optional branch target
- `current_branch()` -- rev-parse HEAD

These are static because they only need a local repo path, not API
authentication. This lets test code call them without mocking the GitHub API.

### Commit

`add_and_commit()` stages files (defaulting to `.` for all) and commits,
returning the short SHA. `set_local_identity()` configures the repo-local
git author so commits in temporary workspaces have consistent attribution.

### Push

`push()` pushes the current branch with `-u` (set-upstream) by default.
It uses `_run_git()` so any token in the remote URL is redacted on failure.

## Pull request lifecycle

### Creation

`create_pr()` calls the PyGithub API to create a PR, returning a `PRResult`
dataclass with number, URL, title, head, and base. Draft PRs are supported
via the `draft` parameter.

### Inspection

- `get_pr()` -- full PR details including mergeable/merged state
- `list_prs()` -- paginated PR listing with state filter
- `default_branch()` -- queries the repo's default branch name
- `get_check_runs()` -- CI status aggregation (success/failure/pending/mixed/no_checks)

### Updates

- `update_pr_body()` -- edits the PR description
- `upsert_pr_comment()` -- creates or updates a marker-tagged comment (idempotent
  status updates using a `<!-- helping_hands:status -->` marker)

The upsert pattern ensures repeated runs update the same comment rather than
creating duplicate status comments.

## Issue lifecycle

### Creation

`create_issue()` calls the PyGithub API to create an issue, returning an
`IssueResult` dataclass with number, URL, and title. Optional `labels` can be
applied at creation time. This is used by the **Project Management** feature
to auto-create a tracking issue from the task prompt before hand execution.

### Inspection

`get_issue()` retrieves issue details including number, title, body, state,
labels, and user.

### PR-issue linking

When `Hand.issue_number` is set (by the celery task when `project_management`
is enabled), `_create_new_pr()` prepends `Closes #N` to the PR body so the
issue is auto-closed when the PR is merged.

## CI check aggregation

`get_check_runs()` aggregates individual GitHub check runs into a single
overall conclusion:

| Condition | Result |
|---|---|
| No check runs | `no_checks` |
| Any run still in progress | `pending` |
| All runs succeeded | `success` |
| Any run failed | `failure` |
| Mixed (some skipped, cancelled, etc.) | `mixed` |

This powers the CI fix loop in CLI hands, which polls check status and retries
on failure.

## Subprocess helper

All local git operations use `_run_git()`, a thin wrapper around
`subprocess.run()` that:

1. Captures stdout and stderr
2. Checks the return code
3. On failure, constructs a redacted error message and raises `RuntimeError`

This centralizes error handling and token safety for every git subprocess call.

## Alternatives considered

- **`gitpython`** -- rejected in favor of subprocess calls for transparency and
  debuggability; git CLI output is easier to log and redact than GitPython's
  internal state.
- **`gh` CLI for API calls** -- rejected because PyGithub provides typed
  objects and doesn't require `gh` to be installed in the runtime environment.
- **SSH-based auth** -- not used; HTTPS with embedded tokens is simpler in
  containers and CI where SSH keys are not available.

## Consequences

- Every git operation is non-interactive by construction (token in URL)
- Token leaks are prevented at the subprocess layer
- Static methods keep local operations testable without API mocking
- `PRResult` dataclass decouples PR creation results from PyGithub internals
