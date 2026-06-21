# GitHub App Authentication

A GitHub App is a server-level alternative to a personal access token (PAT).
Instead of a long-lived `GITHUB_TOKEN`, the server (or CLI) authenticates as a
GitHub App and mints short-lived **installation access tokens** on demand.

## Why it works with no downstream changes

A GitHub App installation access token is drop-in compatible with a PAT:

- It authenticates the REST API via PyGithub's `Auth.Token`.
- It works in token-authenticated HTTPS URLs
  (`https://x-access-token:<token>@github.com/<owner>/<repo>.git`) for clone and
  push.

Because of this, App auth hooks into a single chokepoint —
`resolve_github_token()` in `lib/github_url.py` — and everything downstream
(`GitHubClient`, `build_clone_url`, grill, multiplayer grill, Celery hand
execution, PR finalization) is unaffected.

## Configuration (environment only)

| Env var | Required | Meaning |
|---------|----------|---------|
| `GITHUB_APP_ID` | yes | The App's numeric app id (or client id) |
| `GITHUB_APP_PRIVATE_KEY_PATH` | one of these | Path to the App's `.pem` private key |
| `GITHUB_APP_PRIVATE_KEY` | one of these | Private key contents inline (literal `\n` escapes are unescaped) |
| `GITHUB_APP_INSTALLATION_ID` | optional | Installation id; auto-discovered when the App has exactly one installation |

The path takes precedence over the inline key when both are set. App auth
requires the `github` extra (PyGithub), which is imported lazily so
`lib/github_url` stays importable without it.

## Resolution order

`resolve_github_token(token)` returns the first available of:

1. The explicit `token` argument (e.g. a per-user `X-GitHub-Token`).
2. `GITHUB_TOKEN`.
3. `GH_TOKEN`.
4. A freshly minted GitHub App installation token (when an App is configured).

A configured-but-broken App (missing/unreadable key, no matching installation,
API failure) raises `GitHubAppError` rather than silently falling back to
anonymous access. When no App is configured, step 4 is skipped and resolution
returns `""` as before.

## Token lifetime and caching

Installation tokens expire after ~1 hour. `lib/github_app.py` caches minted
tokens per-process, keyed by `(app id, installation-id env)`, and refreshes a
token a few minutes before it expires. The cache is per-process (each FastAPI
worker / Celery worker mints its own), which is fine — GitHub permits many
concurrent installation tokens. Long-running operations re-resolve at point of
use, so they always get a non-expired token.

## Server credential model

A configured GitHub App counts as **server-owned credentials**, exactly like a
server `GITHUB_TOKEN`. `_server_has_github_token()` returns `True`, so:

- Schedule and template ownership checks are bypassed (no per-user
  `owner_token_hash` enforcement).
- Multiplayer grill session creation and creator-only actions are allowed for
  any caller (`_mgrill_require_token` returns a `""` sentinel meaning "use the
  server's credentials", which the worker resolves to a minted token at clone
  time).

Per-user tokens still take precedence when a client sends `X-GitHub-Token`, so
App auth never perturbs the existing per-user flow.

## What is intentionally out of scope

- **No frontend changes.** The frontend supplies *per-user* tokens; the App is
  a deployment-level credential configured via env on the server/CLI host.
- **No per-repo installation routing.** A single installation is assumed
  (auto-discovered) or selected explicitly via `GITHUB_APP_INSTALLATION_ID`.
  Multi-installation, per-repo token minting could be added later if a single
  deployment needs to act across installations.
