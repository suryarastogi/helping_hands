# PR Description Generation

How helping_hands generates rich PR descriptions and commit messages using
CLI tools, with graceful fallback when no CLI is available.

## Context

When a hand finishes its work and pushes changes, the default git commit
message and PR body are generic (e.g., "helping_hands automated changes").
Rich PR descriptions make reviews easier by summarizing what changed and
why, using conventional commit style.

The `pr_description` module (`lib/hands/v1/hand/pr_description.py`) provides
two generators called from `Hand._finalize_repo_pr()`:

1. **`generate_pr_description()`** -- produces a PR title and body
2. **`generate_commit_message()`** -- produces a single-line commit message

Both are optional: if generation fails or is disabled, the caller falls
back to its existing generic messages.

## Generation flow

### PR description

```
_finalize_repo_pr() calls generate_pr_description(cmd, repo_dir, ...)
        |
        v
  Check: cmd is None? --> return None (no CLI available)
        |
        v
  Check: _is_disabled()? --> return None (env var opt-out)
        |
        v
  _get_diff(repo_dir, base_branch)
        |
        v
  _truncate_diff(diff, limit) -- cap at HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT
        |
        v
  _build_prompt(diff, backend, user_prompt, summary)
        |
        v
  subprocess.run(cmd, input=prompt, timeout=...)
        |
        +-- TimeoutExpired --> return None
        +-- FileNotFoundError --> return None
        +-- Non-zero exit --> return None
        |
        v
  _parse_output(stdout) --> PRDescription(title, body) or None
```

### Commit message

```
generate_commit_message(cmd, repo_dir, ...)
        |
        v
  Check: _is_disabled()? --> return None
        |
        v
  Check: cmd is None? --> _commit_message_from_prompt(prompt, summary)
        |                   (heuristic fallback, no CLI needed)
        v
  _get_uncommitted_diff(repo_dir)  -- stages all changes first
        |
        v
  _build_commit_message_prompt(diff, backend, user_prompt, summary)
        |
        v
  subprocess.run(cmd, input=prompt, timeout=30s)
        |
        +-- TimeoutExpired / FileNotFoundError / non-zero exit --> return None
        |
        v
  _parse_commit_message(stdout) --> "feat: ..." or None
```

## Prompt engineering

Both prompts follow the same structure:

1. **Role instruction** -- "You are generating a PR description / commit message"
2. **Format rules** -- specific marker lines (`PR_TITLE:`, `PR_BODY:`, `COMMIT_MSG:`)
3. **Context section** -- backend name, original task prompt (truncated to 500 chars)
4. **Optional summary** -- AI-generated summary from the hand run (truncated)
5. **Git diff** -- the actual code changes, wrapped in a fenced code block

The output format uses simple marker lines rather than JSON to keep parsing
robust against CLI tools that add preamble or trailing text.

## Parsing

- **PR description**: scans line-by-line for `PR_TITLE:` and `PR_BODY:` markers.
  Returns `None` if either title or body is empty.
- **Commit message**: scans for `COMMIT_MSG:` and truncates to 72 characters.
  Returns `None` if no valid line found.

## Fallback chain

The module is designed to fail gracefully at every stage:

| Failure point | Behavior |
|---|---|
| No CLI command (`cmd=None`) | PR desc: returns `None`; commit msg: heuristic from prompt/summary |
| Disabled via env var | Returns `None` |
| Empty diff | Returns `None` |
| CLI timeout | Logs warning, returns `None` |
| CLI not found | Logs debug, returns `None` |
| CLI non-zero exit | Logs warning, returns `None` |
| Unparseable output | Logs warning, returns `None` |

The heuristic fallback (`_commit_message_from_prompt`) extracts the first
sentence from the summary (preferred) or prompt, strips existing conventional
commit prefixes, and re-formats as `feat: <lowercase first char>`.

## Diff handling

- **PR description diff**: `git diff {base_branch}...HEAD`, falling back to
  `HEAD~1..HEAD` for shallow clones.
- **Commit message diff**: `git diff --cached` after `git add .` (includes
  new files).
- Both diffs are truncated to a configurable character limit before being
  sent to the CLI tool.

## Environment configuration

| Variable | Default | Description |
|---|---|---|
| `HELPING_HANDS_DISABLE_PR_DESCRIPTION` | (unset) | Set to `1`/`true`/`yes`/`on` to disable |
| `HELPING_HANDS_PR_DESCRIPTION_TIMEOUT` | `60` | Timeout in seconds for CLI invocation |
| `HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT` | `12000` | Max diff characters sent to CLI |

Invalid or non-positive values for timeout and diff limit fall back to defaults.

## Design decisions

- **Marker-based output** over JSON: CLI tools may add commentary around
  structured output; simple line-prefix markers are more reliably parsed.
- **Subprocess over SDK**: reuses the same CLI tool (`claude -p`, `gemini -p`)
  that the hand already depends on, avoiding extra SDK dependencies.
- **Side-effect staging for commit messages**: `git add .` is called before
  reading the cached diff so new files appear in the commit message prompt.
  This is acceptable because the subsequent `git commit` uses the same
  staged changes.
- **Separate timeout/limit for commit messages**: commit messages need less
  context (8K chars, 30s timeout) than full PR descriptions (12K chars, 60s).
