"""Generate rich PR descriptions using a CLI tool.

This module provides a self-contained function that invokes a CLI tool
(e.g. ``claude -p``, ``gemini -p``) to produce a descriptive PR title and
body from a git diff.  It is designed to be called from
``Hand._finalize_repo_pr()`` and falls back gracefully when no CLI is
available or generation fails.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DIFF_CHAR_LIMIT = 12_000
_DEFAULT_TIMEOUT_SECONDS = 60.0
_DISABLE_ENV_VAR = "HELPING_HANDS_DISABLE_PR_DESCRIPTION"
_TIMEOUT_ENV_VAR = "HELPING_HANDS_PR_DESCRIPTION_TIMEOUT"
_DIFF_LIMIT_ENV_VAR = "HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT"


@dataclass(frozen=True)
class PRDescription:
    """Parsed PR title and body from CLI output."""

    title: str
    body: str


def _is_disabled() -> bool:
    """Check whether rich PR description generation is explicitly disabled."""
    raw = os.environ.get(_DISABLE_ENV_VAR, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _timeout_seconds() -> float:
    """Return the configured timeout for CLI invocation."""
    raw = os.environ.get(_TIMEOUT_ENV_VAR)
    if raw is None:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw.strip())
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else _DEFAULT_TIMEOUT_SECONDS


def _diff_char_limit() -> int:
    """Return the maximum number of characters for the diff."""
    raw = os.environ.get(_DIFF_LIMIT_ENV_VAR)
    if raw is None:
        return _DEFAULT_DIFF_CHAR_LIMIT
    try:
        value = int(raw.strip())
    except ValueError:
        return _DEFAULT_DIFF_CHAR_LIMIT
    return value if value > 0 else _DEFAULT_DIFF_CHAR_LIMIT


def _get_diff(repo_dir: Path, *, base_branch: str) -> str:
    """Get the git diff between the current HEAD and *base_branch*.

    Falls back to ``HEAD~1..HEAD`` if the base-branch comparison fails
    (e.g. shallow clone without the base ref).
    """
    result = subprocess.run(
        ["git", "diff", f"{base_branch}...HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    return ""


def _truncate_diff(diff: str, *, limit: int) -> str:
    """Truncate *diff* to stay within *limit* characters."""
    if len(diff) <= limit:
        return diff
    return f"{diff[:limit]}\n...[truncated — {len(diff) - limit} chars omitted]"


def _build_prompt(
    *,
    diff: str,
    backend: str,
    user_prompt: str,
    summary: str,
) -> str:
    """Build the prompt that asks the CLI to generate a PR description."""
    summary_section = ""
    if summary.strip():
        truncated = summary.strip()[:2000]
        summary_section = f"\n## AI Summary of Changes\n{truncated}\n"

    return (
        "You are generating a pull request title and description for a code change.\n\n"
        "Instructions:\n"
        "- Write a concise, informative PR title (under 72 characters).\n"
        "- Write a clear PR body in markdown that explains what changed and why.\n"
        "- Include a brief summary of the key changes.\n"
        "- If the diff is large, focus on the most important changes.\n"
        "- Do not include the raw diff in the body.\n"
        "- Use conventional commit style for the title "
        "(e.g., feat:, fix:, refactor:, docs:).\n\n"
        "Output format — use EXACTLY these markers:\n"
        "PR_TITLE: <your title here>\n"
        "PR_BODY:\n"
        "<your markdown body here>\n\n"
        f"## Context\n"
        f"- Backend: {backend}\n"
        f"- Original task prompt: {user_prompt[:500]}\n"
        f"{summary_section}\n"
        f"## Git Diff\n"
        f"```diff\n{diff}\n```\n"
    )


def _parse_output(output: str) -> PRDescription | None:
    """Parse CLI output into a ``PRDescription``.

    Returns ``None`` if the output cannot be parsed.
    """
    title = ""
    body_start_idx: int | None = None

    lines = output.split("\n")
    for idx, line in enumerate(lines):
        if line.startswith("PR_TITLE:"):
            title = line[len("PR_TITLE:") :].strip()
        elif line.strip() == "PR_BODY:":
            body_start_idx = idx + 1
            break

    if not title:
        return None

    body = ""
    if body_start_idx is not None and body_start_idx < len(lines):
        body = "\n".join(lines[body_start_idx:]).strip()

    if not body:
        return None

    return PRDescription(title=title, body=body)


def generate_pr_description(
    *,
    cmd: list[str] | None,
    repo_dir: Path,
    base_branch: str,
    backend: str,
    prompt: str,
    summary: str,
) -> PRDescription | None:
    """Generate a rich PR description using a CLI tool.

    Returns a ``PRDescription`` with title and body, or ``None`` if
    generation is disabled, unavailable, or fails.

    Args:
        cmd: CLI command to invoke (e.g. ``["claude", "-p"]``).
            The prompt text is passed via stdin.  ``None`` skips generation.
        repo_dir: Path to the git repository root.
        base_branch: The target branch for the PR.
        backend: The hand backend name (e.g., ``"claudecodecli"``).
        prompt: The original user task prompt.
        summary: The AI-generated summary from the hand run.
    """
    if cmd is None:
        return None

    if _is_disabled():
        logger.debug("Rich PR description generation is disabled.")
        return None

    diff = _get_diff(repo_dir, base_branch=base_branch)
    if not diff:
        logger.debug("No diff available; skipping rich PR description.")
        return None

    limit = _diff_char_limit()
    truncated_diff = _truncate_diff(diff, limit=limit)

    cli_prompt = _build_prompt(
        diff=truncated_diff,
        backend=backend,
        user_prompt=prompt,
        summary=summary,
    )

    cli_label = cmd[0] if cmd else "cli"
    timeout = _timeout_seconds()
    try:
        result = subprocess.run(
            cmd,
            input=cli_prompt,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "%s PR description generation timed out after %.0fs.",
            cli_label,
            timeout,
        )
        return None
    except FileNotFoundError:
        logger.debug("%s CLI not found at execution time.", cli_label)
        return None

    if result.returncode != 0:
        logger.warning(
            "%s PR description generation failed (exit=%d): %s",
            cli_label,
            result.returncode,
            result.stderr.strip()[-500:],
        )
        return None

    parsed = _parse_output(result.stdout)
    if parsed is None:
        logger.warning(
            "Could not parse %s PR description output. Output (last 500 chars): %s",
            cli_label,
            result.stdout.strip()[-500:],
        )
        return None

    logger.info("Generated rich PR description via %s: %s", cli_label, parsed.title)
    return parsed
