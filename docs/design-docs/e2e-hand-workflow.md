# E2E Hand Workflow

The `E2EHand` is the minimal concrete `Hand` implementation that validates the
full clone/edit/commit/push/PR lifecycle against a real GitHub repository.

## Context

Every hand backend (CLI, iterative, LangGraph, Atomic) relies on the base
`Hand` class for finalization (commit/push/PR). `E2EHand` exercises this
pipeline end-to-end without involving AI providers, making it the definitive
integration test for the GitHub plumbing layer. It is invoked via `--e2e` on
the CLI and used by the app worker for smoke-test validation tasks.

## Lifecycle

```
1. Resolve repo and workspace
2. Determine base branch (configured / API default / clone detection)
3. Clone repository (shallow, depth=1)
4. Create or resume branch
5. Write deterministic marker file
6. Commit, push, create/update PR (unless dry-run)
7. Update PR body and upsert status comment
8. Return HandResponse with full metadata
```

### Step 1: Workspace resolution

The workspace is derived from `hand_uuid` (auto-generated UUID4 if not
provided) and an optional `HELPING_HANDS_WORK_ROOT` env var:

```
{HELPING_HANDS_WORK_ROOT}/{hand_uuid}/git/{safe_repo}/
```

`_safe_repo_dir` sanitizes the `owner/repo` string to a filesystem-safe name
by replacing non-alphanumeric characters with underscores.

### Step 2: Base branch resolution

Three-tier fallback:

1. **Explicit env** -- `HELPING_HANDS_BASE_BRANCH` overrides everything.
2. **Resumed PR** -- When `pr_number` is provided, the PR's base ref is used.
3. **API default** -- `GitHubClient.default_branch(repo)` fetches the repo
   default. If the API call fails, the clone proceeds without a branch arg and
   the detected branch is used as base.

### Step 3: Clone

`GitHubClient.clone()` with `depth=1` for speed. When clone_branch is `None`
(API default failed), the clone uses whatever the remote HEAD points to, and
the detected branch is captured via `GitHubClient.current_branch()`.

### Step 4: Branch management

- **Fresh PR**: `GitHubClient.create_branch()` creates
  `helping-hands/e2e-{uuid[:8]}` from the base branch.
- **Resumed PR**: `GitHubClient.fetch_branch()` + `switch_branch()` to the
  PR's head ref, preserving the existing branch name.

### Step 5: Marker file

A deterministic `HELPING_HANDS_E2E.md` file is written with hand UUID, prompt,
and UTC timestamp. This produces a guaranteed diff for the commit step.

### Step 6: Commit and push (non-dry-run)

- Git identity is set via `HELPING_HANDS_GIT_USER_NAME` / `_EMAIL` env vars
  (defaults: `helping-hands[bot]` / noreply address).
- `GitHubClient.add_and_commit()` stages only the marker file.
- `GitHubClient.push()` with `set_upstream=True`.

### Step 7: PR management

- **Fresh PR**: `GitHubClient.create_pr()` with a deterministic title and
  body containing UUID, prompt, timestamp, and commit SHA.
- **Resumed PR**: Body updated via `update_pr_body()`, status comment upserted
  via `upsert_pr_comment()` with marker `<!-- helping_hands:e2e-status -->`.

### Dry-run mode

When `dry_run=True`, the clone, branch creation, and marker file write all
proceed normally, but commit/push/PR operations are skipped entirely. This
validates workspace setup without side effects on GitHub.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `HELPING_HANDS_WORK_ROOT` | `.` | Workspace root directory |
| `HELPING_HANDS_BASE_BRANCH` | (API default) | Override base branch |
| `HELPING_HANDS_GIT_USER_NAME` | `helping-hands[bot]` | Git commit author name |
| `HELPING_HANDS_GIT_USER_EMAIL` | `helping-hands-bot@users.noreply.github.com` | Git commit author email |

## HandResponse metadata

The returned `HandResponse.metadata` dict contains:

| Key | Description |
|---|---|
| `backend` | Always `"e2e"` |
| `model` | Config model string |
| `hand_uuid` | UUID for this run |
| `hand_root` | Workspace root path |
| `repo` | GitHub `owner/repo` |
| `workspace` | Full clone directory path |
| `branch` | Working branch name |
| `base_branch` | Target merge base |
| `commit` | Commit SHA (empty if dry-run) |
| `pr_number` | PR number (empty string if none) |
| `pr_url` | PR URL (empty string if none) |
| `resumed_pr` | `"true"` or `"false"` |
| `dry_run` | `"true"` or `"false"` |

## Relationship to other hands

`E2EHand` inherits `Hand` but does **not** use the base class finalization
(`_finalize_repo_pr`). Instead, it manages the full GitHub lifecycle directly
because it owns the clone workspace and needs deterministic marker-file content.

Other hands (CLI, iterative) work on existing local repos and delegate
finalization to the base class, which handles commit/push/PR generically.

## Key source files

- `src/helping_hands/lib/hands/v1/hand/e2e.py` -- E2EHand implementation
- `src/helping_hands/lib/hands/v1/hand/base.py` -- Hand base class
- `src/helping_hands/lib/github.py` -- GitHubClient (clone, branch, PR ops)
