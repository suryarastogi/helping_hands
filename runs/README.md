# Runs Directory

This directory stores per-hand runtime workspaces and artifacts.

Expected layout:

- `{hand_uuid}/git/{repo}`

Each `hand_uuid` directory is a self-contained filesystem environment for a single hand run.

Repository checkout and modifications for that run happen under `git/{repo}`.

Notes:

- Runtime contents in this directory are intentionally ignored by git.
- This `README.md` is tracked to document the convention.
