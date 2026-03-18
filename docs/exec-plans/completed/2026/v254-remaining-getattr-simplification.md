# v254: Simplify remaining getattr() to direct attribute access

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

Four remaining `getattr()` calls across the codebase used defensive attribute
access for attributes that are guaranteed to exist on their respective objects:

1. `web.py` `browse_url()`: `getattr(response, "status", None)` — `HTTPResponse`
   from `urlopen()` always has `.status`
2. `base.py` `finalize_pr()`: `getattr(repo_obj, "default_branch", "")` — PyGithub
   `Repository` always has `.default_branch`
3. `app.py` `update_schedule()`: `getattr(existing, "github_token", None)` —
   `ScheduledTask` dataclass has `.github_token` with default `None`
4. `celery_app.py` `run_hand()`: nested `getattr(getattr(self, "request", None), "id", None)` —
   Celery bound task always has `self.request.id`

## Tasks

- [x] Replace `getattr(response, "status", None)` with `response.status` in `web.py`
- [x] Replace `getattr(repo_obj, "default_branch", "")` with `repo_obj.default_branch` in `base.py`
- [x] Replace `getattr(existing, "github_token", None)` with `existing.github_token` in `app.py`
- [x] Replace nested `getattr(getattr(self, "request", None), "id", None)` with `self.request.id` in `celery_app.py`
- [x] Add AST/source-based tests confirming no getattr remains in target locations
- [x] Add ScheduledTask.github_token default/value verification tests
- [x] Verify all existing tests pass

## Completion criteria

- No unnecessary `getattr()` calls remain in the four target locations
- All existing tests pass (5960 passed, 270 skipped)
- New tests verify source consistency and attribute access correctness
