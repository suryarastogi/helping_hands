# MCP Architecture

How helping_hands exposes capabilities over the Model Context Protocol.

## Context

The MCP server lets AI clients (Claude Desktop, Cursor, other IDE integrations)
use helping_hands as a tool provider. It wraps the same core library used by the
CLI and FastAPI server, providing a consistent interface through the MCP
protocol.

## Transport selection

The server supports two transport modes, selected at startup:

| Mode | Flag | Use case |
|---|---|---|
| stdio | (default) | Claude Desktop, Cursor, local IDE integration |
| streamable-http | `--http` | Networked clients, remote integrations |

Transport is determined by a simple `sys.argv` check in `main()`. Both modes
use the same `FastMCP` instance and tool registrations.

## Tool registration

All tools are registered via `@mcp.tool()` decorators on module-level
functions. The server exposes three categories:

### Repository tools

| Tool | Description | Backed by |
|---|---|---|
| `index_repo` | Walk a local repo and return file listing | `RepoIndex.from_path()` |
| `read_file` | Read a UTF-8 file from a repository | `filesystem.read_text_file()` |
| `write_file` | Write a UTF-8 file in a repository | `filesystem.write_text_file()` |
| `mkdir` | Create a directory in a repository | `filesystem.mkdir_path()` |
| `path_exists` | Check whether a repo-relative path exists | `filesystem.path_exists()` |

### Execution tools

| Tool | Description | Backed by |
|---|---|---|
| `run_python_code` | Execute inline Python code | `command.run_python_code()` |
| `run_python_script` | Execute a repo-relative Python script | `command.run_python_script()` |
| `run_bash_script` | Execute a repo-relative or inline bash script | `command.run_bash_script()` |

### Web and task tools

| Tool | Description | Backed by |
|---|---|---|
| `web_search` | Search the web (DuckDuckGo) | `web.search_web()` |
| `web_browse` | Browse and extract text from a URL | `web.browse_url()` |
| `build_feature` | Enqueue an async hand task via Celery | `celery_app.build_feature.delay()` |
| `get_task_status` | Check status of an enqueued task | `celery_app.build_feature.AsyncResult()` |
| `get_config` | Return current helping_hands configuration | `Config.from_env()` |

## Repo isolation

All filesystem operations route through the shared `meta/tools/filesystem.py`
layer, which enforces path safety via `resolve_repo_target()`. This prevents
path traversal attacks — a client cannot read or write files outside the
repository root, even through symlinks or `..` components.

The MCP server maintains an in-memory `_indexed_repos` dict mapping resolved
paths to `RepoIndex` instances. Each `index_repo` call updates this cache.

## Error handling

MCP tool functions re-raise domain-specific exceptions with clear messages:

- `FileNotFoundError` — file or repo path does not exist
- `IsADirectoryError` — attempted to read a directory as a file
- `UnicodeError` — file is not valid UTF-8 text
- `ValueError` — invalid or unsafe file path (path traversal blocked)

These map naturally to MCP error responses and give clients actionable
feedback.

## Resources

The server also exposes one MCP resource:

- `repo://indexed` — Lists all currently indexed repositories with file counts

## Design decisions

1. **Thin wrappers** — MCP tool functions are thin wrappers around core library
   functions. No business logic lives in the MCP layer; it only handles
   parameter validation and error translation.

2. **Lazy Celery imports** — `build_feature` and `get_task_status` import
   Celery task references inside the function body to avoid requiring Celery
   as a hard dependency of the MCP server.

3. **Shared tool layer** — The same `filesystem`, `command`, and `web` modules
   serve both MCP tools and iterative hand in-model operations (`@@READ`,
   `@@FILE`). Bug fixes and security hardening apply to both surfaces.

4. **No authentication** — The MCP server trusts its transport layer (stdio
   pipe or local HTTP) for access control. It does not implement its own
   auth. This is appropriate for local IDE integrations but would need
   extension for multi-tenant deployments.
