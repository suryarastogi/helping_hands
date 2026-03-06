# Repo Indexing

How helping_hands ingests and indexes repositories for AI agent consumption.

## Context

Every hand needs a structural map of the repository it operates on.  The
`RepoIndex` dataclass (`lib/repo.py`) provides this map: a root path and a
sorted list of all tracked files.  This index feeds into system prompts,
bootstrap context, and file-resolution logic across the codebase.

## Design

### `RepoIndex.from_path`

The primary entry point is `RepoIndex.from_path(path)`, which:

1. **Validates** the path is a directory (raises `FileNotFoundError` otherwise).
2. **Walks** the tree using `Path.rglob("*")`, collecting all regular files.
3. **Filters** out `.git/` internals by checking `".git" not in p.parts`.
4. **Sorts** file paths alphabetically for deterministic ordering.
5. **Returns** a `RepoIndex` with relative path strings.

```python
@dataclass
class RepoIndex:
    root: Path
    files: list[str]

    @classmethod
    def from_path(cls, path: Path) -> RepoIndex: ...
```

### Why relative paths

Files are stored as relative path strings (e.g. `"src/main.py"`) rather than
absolute `Path` objects.  This makes the index portable across clone locations
and keeps system prompt payloads clean.

### `.git` exclusion

The filter `".git" not in p.parts` excludes everything under `.git/` — objects,
refs, hooks, etc.  This is a parts-based check (not a prefix check) so it
correctly handles paths like `docs/.gitignore` (included) vs `.git/config`
(excluded).

## Consumers

| Consumer | How it uses RepoIndex |
|---|---|
| Iterative hands (`_build_tree_snapshot`) | Builds a bounded-depth tree string from `files` for the system prompt |
| CLI hands (`_build_init_prompt`) | Lists up to 200 files from `files` in the init phase prompt |
| E2E hand | Passes the index through to finalization |
| MCP server | Uses `root` for path-safe file operations |
| `conftest.py` fixtures | `repo_index` and `make_cli_hand` create minimal indexes for testing |

## Alternatives considered

- **gitpython / pygit2** — Adds a heavy dependency for something `pathlib.rglob`
  handles in 5 lines.  We already shell out to `git` for operations that need it
  (via `GitHubClient`).
- **Lazy file listing** — Could defer the walk until first access, but the index
  is always needed immediately and the walk is fast for typical repos.
- **Content hashing** — Considered storing file hashes for change detection, but
  `git diff` already handles this for the PR workflow.

## Consequences

- The index is built once per hand invocation and treated as immutable.
- Very large repos (100k+ files) will produce large `files` lists; the
  `_build_tree_snapshot` and `_build_init_prompt` consumers cap output to avoid
  prompt bloat.
- No `.gitignore` awareness beyond `.git/` exclusion — all non-git files are
  indexed.  This is intentional: agents should see the full repo structure
  including build artifacts and generated files.
