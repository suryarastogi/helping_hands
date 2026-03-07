# Filesystem Security

How helping_hands confines AI-generated file operations to the target
repository, preventing path traversal and unauthorized access.

## Context

AI agents produce file paths as part of their output (`@@FILE`, `@@READ`,
MCP tool calls). These paths are untrusted user input from a security
perspective -- the AI can hallucinate or be manipulated into targeting
files outside the repository. A single layer of defence is needed to
prevent all filesystem operations from escaping the repo root.

## Decision

All file I/O routes through `resolve_repo_target()` in
`src/helping_hands/lib/meta/tools/filesystem.py`. This function is the
single chokepoint for path confinement.

### Resolution algorithm

```
1. Resolve repo_root to an absolute path (eliminates symlink tricks)
2. Normalize rel_path: strip whitespace, convert backslashes, remove "./"
3. Reject if empty or starts with "/" (absolute path)
4. Join repo_root + normalized path, resolve to absolute
5. Call target.relative_to(root) -- raises ValueError if target
   is not a descendant of root
```

Step 5 is the critical guard: after symlink resolution and `..` collapse,
the resolved target must still be under the repo root. This catches:

- `../../etc/passwd` -- collapses to a path outside root
- Symlink targets pointing outside the repo
- Encoded path separators (`%2F`, `%2E%2E`) -- handled by Path resolution

### Shared by all consumers

The same `resolve_repo_target()` function is called by:

| Consumer | Entry point |
|---|---|
| Iterative hands (`@@FILE`, `@@READ`) | `_apply_inline_edits()`, `_execute_read_requests()` |
| MCP server tools | `read_file`, `write_file`, `mkdir`, `path_exists` handlers |
| Filesystem module | `read_text_file()`, `write_text_file()`, `mkdir_path()` |

No file operation bypasses this check. Adding a new filesystem tool
requires routing through `resolve_repo_target()`.

### Error behavior

Invalid paths raise `ValueError("invalid path")`. Callers convert this
to user-facing error messages without leaking the resolved absolute path.

## Companion controls

Path confinement is the primary defence. Additional layers reduce blast
radius:

- **Subprocess sandboxing** -- Codex CLI `workspace-write` mode limits
  filesystem access at the OS level. Docker containers limit access at
  the namespace level.
- **Non-interactive git** -- `GIT_TERMINAL_PROMPT=0` prevents credential
  prompts that could leak information.
- **Opt-in execution tools** -- `python.run_code` and `bash.run_script`
  are disabled by default. When enabled, they execute without path
  confinement (documented as elevated privilege).
- **Docker sandbox (microVM)** -- `DockerSandboxClaudeCodeHand` runs
  inside a Docker Desktop microVM with only the target repo synced in.

## Alternatives considered

- **Chroot / namespace isolation** -- Too heavy for CLI mode, not portable
  across macOS/Linux. Docker already provides this for app mode.
- **Allowlist of file extensions** -- Overly restrictive; AI agents need to
  create arbitrary files (configs, scripts, docs).
- **Per-operation confirmation** -- Impractical for automated runs. The
  whole point is non-interactive execution.

## Consequences

- All filesystem tools are centralized in one module, making auditing easy
- New file operations must use `resolve_repo_target()` or they bypass
  security -- this is enforced by convention, not by the type system
- Execution tools (`run_python_code`, `run_bash_script`) intentionally
  bypass path confinement because they run arbitrary code; this is
  documented in SECURITY.md as requiring `--enable-execution`
- Symlink-following behavior means a symlink inside the repo that points
  outside will be rejected -- this is correct and intentional

## Test coverage

`test_filesystem.py` covers:
- Traversal attempts (`../`, `../../`, absolute paths)
- Empty and whitespace-only paths
- Backslash normalization
- `./` prefix stripping
- Symlink resolution (when relevant)
- Read/write/mkdir through the public API
- Max-chars truncation for reads
- Error types (FileNotFoundError, IsADirectoryError, UnicodeError)
