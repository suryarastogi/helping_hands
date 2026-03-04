# Security Model

## Path Confinement

All filesystem operations are routed through `src/helping_hands/lib/meta/tools/filesystem.py`:

- `resolve_repo_target()` resolves and validates paths against the repo root
- Traversal attempts (`../`, absolute paths) raise `ValueError`
- Symlinks are resolved before confinement checks

## Authentication

- GitHub operations use `GITHUB_TOKEN` — token-authenticated, non-interactive
- No OS credential popup in automation contexts
- API keys are loaded from environment variables, never hard-coded

## Command Execution

- Command tools in `meta/tools/command.py` run in subprocess with controlled arguments
- Working directory is confined to the repo root
- Timeout enforcement prevents runaway processes

## Input Validation

- AI model strings are validated through provider resolution
- CLI inputs are parsed through argparse with type enforcement
- Server endpoints use Pydantic models for request validation
