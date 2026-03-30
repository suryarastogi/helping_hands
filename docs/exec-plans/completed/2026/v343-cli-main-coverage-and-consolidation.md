# v343 — CLI Main Coverage & Daily Consolidation

**Status:** Completed
**Created:** 2026-03-30
**Date:** 2026-03-30
**Theme:** Close last testable non-server coverage gap + docs housekeeping

## Goals

1. **Close `cli/main.py` branch 336→339** — the `if args.max_iterations is not None` False
   path (max_iterations not supplied). Change argparse default from `6` to `None` so both
   branches are reachable, then add tests.
2. **Update tech debt tracker** — add `cli/main.py` `if __name__ == "__main__"` guard
   (line 525) as untestable, matching the existing `mcp_server.py` entry.
3. **Update 2026-03-30 daily consolidation** — add v342 (server helper coverage) which
   was completed today but not yet included in the daily file.

## Non-goals

- Server-extras coverage (requires `--extra server` install)
- Chasing untestable branch partials already in tech debt

## Tasks

- [x] Change `--max-iterations` argparse default from `6` to `None`
- [x] Write tests for max_iterations=None (False branch) and explicit value (True branch)
- [x] Verify branch 336→339 is now covered
- [x] Update `tech-debt-tracker.md` with `cli/main.py` guard
- [x] Update `2026-03-30.md` daily consolidation with v342 and v343
- [x] Update PLANS.md to reference plan
- [x] Move this plan to completed, update INTENT.md

## Completion criteria

- `cli/main.py` shows 99% coverage with only line 525 (`__name__` guard) missing
- Branch 336→339 no longer appears in coverage report
- Tech debt tracker includes `cli/main.py` guard entry
- Daily consolidation file includes v342
- All tests pass
