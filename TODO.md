# Project todos

## Open items

- [x] gitignore E2E test files
  Added `frontend/test-results/`, `frontend/playwright-report/`, `frontend/blob-report/` to `.gitignore` (v136). Runtime hand workspaces were already ignored via `runs/*`.

- [x] commit message created by claudecodecli still mediocre
  Added `_is_trivial_message()` guard to reject trivially short/meaningless messages like `feat: -` or `feat: ...` in both `_parse_commit_message()` and `_commit_message_from_prompt()` (v136).