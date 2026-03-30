# GitHub Issue Integration

Design of the issue lifecycle, auto-creation, status sync, and GitHub Projects
integration features in helping_hands.

## Context

When a user kicks off a build, they may want the work tracked as a GitHub issue:
linked to an existing issue, auto-created from the prompt, synced with build
status, and placed on a GitHub Projects board. These features were added in
v325–v329 and extend the existing `GitHubClient` to cover the full issue
lifecycle alongside the PR lifecycle.

All issue operations are best-effort — failures are logged but never block the
build from proceeding.

## Data flow

```
Frontend (FormState)
  ├─ issue_number: int | None
  ├─ create_issue: bool
  └─ project_url: str | None
        │
        ▼
  BuildRequest (server/app.py)
        │
        ▼
  Celery build_feature task
        │
        ├─ _try_create_issue()     → auto-create issue, set hand.issue_number
        ├─ _try_add_to_project()   → add issue to Projects v2 board
        ├─ _sync_issue_status()    → post "running" comment
        │
        │  … hand executes …
        │
        ├─ _sync_issue_status()    → post "completed" or "failed" comment
        └─ Hand finalization       → PR body includes "Closes #N"
```

## Issue creation

When `create_issue=True` and no `issue_number` is provided,
`_try_create_issue()` in `celery_app.py`:

1. Derives a title from the first line of the prompt (≤120 chars), prefixed
   with `[helping-hands]`
2. Calls `GitHubClient.create_issue()` with the full prompt as body and the
   `helping-hands` label
3. Sets `hand.issue_number` so downstream finalization includes `Closes #N`

`GitHubClient.create_issue()` wraps `PyGithub.Repository.create_issue()`,
validating the title is non-empty and forwarding optional labels.

## Issue linking

When `issue_number` is set (either by the user or by auto-creation):

- `Hand` base class appends `\n\nCloses #N` to the PR body
- A comment is posted on the issue linking to the created/updated PR
- The issue number is included in Celery progress metadata so the frontend
  can display an `#N` badge during polling

## Status sync

`_sync_issue_status()` posts or updates a single marker-tagged comment
(`<!-- helping_hands:issue_status -->`) on the linked issue at each lifecycle
point:

| Status | Emoji | Content |
|---|---|---|
| running | 🔄 | "Task is running" |
| completed | ✅ | "Task completed" + PR URL |
| failed | ❌ | "Task failed" + error (≤200 chars) |

Uses `upsert_pr_comment()` for idempotent updates — repeated runs update the
same comment rather than creating duplicates.

## Label management

Two `GitHubClient` methods manage issue labels during builds:

- `add_issue_labels()` — adds labels, auto-creating any that don't exist on
  the repo (with default grey colour)
- `remove_issue_label()` — removes a label, silently ignoring if not present

The Celery helpers use these to swap lifecycle labels:
`helping-hands:in-progress` → `helping-hands:completed` or
`helping-hands:failed`.

## GitHub Projects v2 integration

`_try_add_to_project()` adds the linked issue to a GitHub Projects v2 board
after issue creation/linking and before hand execution.

**URL parsing:** `GitHubClient.parse_project_url()` parses URLs like
`https://github.com/orgs/myorg/projects/5` into
`(owner_type, owner, number)` — supporting both org and user projects.

**GraphQL flow** (`add_to_project_v2()`):

1. Resolve the project node ID via `_graphql()` using an org or user query
2. Resolve the content node ID (issue/PR) from `full_name` + `issue_number`
3. Call `addProjectV2ItemById` mutation to add the item

`_graphql()` is a thin helper that sends GraphQL queries via
`urllib.request` with the GitHub token, returning the `data` payload
or raising `RuntimeError` on errors.

## Error handling

Every issue operation follows the same pattern:

```python
try:
    # issue/project operation
except Exception:
    logger.warning("...", exc_info=True)
    updates.append("⚠️ ...")
```

Failures are logged and appended to the progress update list but never raise.
This ensures a broken GitHub API or permission issue doesn't prevent the
actual build from completing.

## Alternatives considered

- **GitHub Apps** for richer permissions — deferred; PAT-based auth covers
  the current use case and avoids OAuth app installation complexity.
- **REST API for Projects** — not available; GitHub Projects v2 is
  GraphQL-only.
- **Blocking on issue sync failures** — rejected; issue tracking is
  secondary to the actual code generation work.

## Consequences

- Issue lifecycle is fully automated: create → label → sync → close on merge
- All issue operations are best-effort, preserving build reliability
- `project_url` + `issue_number` + `create_issue` fields flow end-to-end
  through frontend → API → Celery → GitHubClient
- GraphQL dependency introduced for Projects v2 (REST API does not support it)
- Label auto-creation avoids requiring users to pre-configure repo labels
