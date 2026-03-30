"""Generate rich PR descriptions and commit messages using a CLI tool.

This module provides self-contained functions that invoke a CLI tool
(e.g. ``claude -p``, ``gemini -p``) to produce a descriptive PR title and
body from a git diff, as well as meaningful commit messages.  It is designed
to be called from ``Hand._finalize_repo_pr()`` and falls back gracefully
when no CLI is available or generation fails.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from subprocess import TimeoutExpired

from helping_hands.lib.config import _is_truthy_env
from helping_hands.lib.validation import (
    require_non_empty_string,
    require_positive_int,
)

logger = logging.getLogger(__name__)

__all__ = ["PRDescription", "generate_commit_message", "generate_pr_description"]

_DEFAULT_DIFF_CHAR_LIMIT = 12_000
_DEFAULT_TIMEOUT_SECONDS = 60.0
_DISABLE_ENV_VAR = "HELPING_HANDS_DISABLE_PR_DESCRIPTION"
_TIMEOUT_ENV_VAR = "HELPING_HANDS_PR_DESCRIPTION_TIMEOUT"
_DIFF_LIMIT_ENV_VAR = "HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT"

_GIT_DIFF_TIMEOUT_S = 30
"""Timeout in seconds for git diff subprocess calls."""

_PR_SUMMARY_TRUNCATION_LENGTH = 2000
"""Maximum characters of summary included in the PR description prompt."""

_COMMIT_SUMMARY_TRUNCATION_LENGTH = 1000
"""Maximum characters of summary included in the commit message prompt."""

_PROMPT_CONTEXT_LENGTH = 500
"""Maximum characters of the user prompt included as context."""

_PR_ERROR_TAIL_LENGTH = 500
"""Trailing characters of CLI output kept in PR generation error/debug logs."""

_COMMIT_ERROR_TAIL_LENGTH = 300
"""Trailing characters of CLI output kept in commit message error/debug logs."""

_GIT_NOT_FOUND_DIFF_MSG = "git not found on PATH; cannot compute diff"
"""Debug message when ``git`` is missing and a staged/committed diff is needed."""

_GIT_NOT_FOUND_UNCOMMITTED_MSG = (
    "git not found on PATH; cannot compute uncommitted diff"
)
"""Debug message when ``git`` is missing and an uncommitted diff is needed."""

_CLI_NOT_FOUND_MSG = "%s CLI not found"
"""Debug template when the description/commit-message CLI binary is missing."""

_COMMIT_MSG_MAX_LENGTH = 72
"""Maximum length for generated commit messages (conventional commit standard)."""

_PR_TITLE_MARKER = "PR_TITLE:"
"""Marker prefix for the PR title line in CLI output."""

_PR_BODY_MARKER = "PR_BODY:"
"""Marker prefix for the PR body section in CLI output."""

_COMMIT_MSG_MARKER = "COMMIT_MSG:"
"""Marker prefix for the commit message line in CLI output."""

_COMMIT_TYPE_PREFIX_RE = re.compile(
    r"^(feat|fix|refactor|docs|chore|test|style|ci|perf|build)"
    r"(\([^)]*\))?\s*:\s*",
    re.IGNORECASE,
)
"""Compiled regex matching a conventional commit type prefix with optional scope."""

_BRACKET_BANNER_RE = re.compile(r"^\[.+?\]\s")
"""Compiled regex matching ``[label] ...`` CLI banner lines."""

_NUMBERED_LIST_RE = re.compile(r"^\d+\.\s")
"""Compiled regex matching numbered list items like ``1. ...``."""


def _truncate_text(text: str, *, limit: int) -> str:
    """Truncate *text* to *limit* characters with a truncation indicator.

    Unlike ``_truncate_diff``, this is designed for prompt/summary context
    where the AI needs to know context was cut off (to avoid generating
    generic or meaningless output from incomplete input).
    """
    require_positive_int(limit, "limit")
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[:limit]}...[truncated]"


_COMMIT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fix": ("fix", "bug", "patch", "hotfix", "repair", "resolve", "crash"),
    "refactor": ("refactor", "restructure", "reorganize", "clean up", "simplify"),
    "docs": ("document", "docs", "readme", "comment"),
    "test": ("test", "spec", "coverage"),
    "ci": ("ci", "pipeline", "workflow", "github action"),
    "style": ("style", "format", "lint", "whitespace"),
    "perf": ("perf", "performance", "optimize", "speed"),
    "chore": ("chore", "bump", "upgrade", "dependency", "dependencies"),
}
"""Keyword mapping for inferring conventional commit type from text.

Order matters: earlier entries take priority when text matches multiple
types.  ``chore`` is last as a catch-all for maintenance tasks.
"""


def _infer_commit_type(text: str) -> str:
    """Infer the conventional commit type from *text* content.

    Scans *text* for keywords associated with each commit type and returns
    the best match.  Uses word-boundary matching to avoid false positives
    (e.g. ``"ci"`` should not match ``"dependencies"``).
    Defaults to ``"feat"`` when no keywords match.
    """
    lower = text.lower()
    for commit_type, keywords in _COMMIT_TYPE_KEYWORDS.items():
        for kw in keywords:
            if " " in kw:
                # Multi-word keywords use simple substring match.
                if kw in lower:
                    return commit_type
            elif len(kw) <= 2:
                # Very short keywords (e.g. "ci") need full word-boundary
                # match to avoid false positives like "dependencies".
                if re.search(rf"\b{re.escape(kw)}\b", lower):
                    return commit_type
            else:
                # Longer keywords use word-start boundary to allow
                # inflected forms (e.g. "test" matches "tests",
                # "refactor" matches "refactored").
                if re.search(rf"\b{re.escape(kw)}", lower):
                    return commit_type
    return "feat"


@dataclass(frozen=True)
class PRDescription:
    """Parsed PR title and body from CLI output.

    Attributes:
        title: One-line PR title extracted from the AI response.
        body: Markdown PR body with summary and change details.
    """

    title: str
    body: str


def _parse_positive_env_var[T: (int, float)](
    env_name: str,
    default: T,
    type_fn: type[T],
) -> T:
    """Parse a positive numeric value from an environment variable.

    Returns *default* when the variable is unset, non-numeric, or
    non-positive, logging a warning for the latter two cases.

    Args:
        env_name: Name of the environment variable to read.
        default: Fallback value when the variable is absent or invalid.
        type_fn: Numeric type constructor (``int`` or ``float``).
    """
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    try:
        value = type_fn(raw.strip())
    except ValueError:
        logger.warning(
            "ignoring non-numeric %s=%r, using default %s",
            env_name,
            raw,
            default,
        )
        return default
    if value <= 0:
        logger.warning(
            "ignoring non-positive %s=%r, using default %s",
            env_name,
            raw,
            default,
        )
        return default
    return value


def _is_disabled() -> bool:
    """Check whether rich PR description generation is explicitly disabled."""
    return _is_truthy_env(_DISABLE_ENV_VAR)


def _timeout_seconds() -> float:
    """Return the configured timeout for CLI invocation."""
    return _parse_positive_env_var(_TIMEOUT_ENV_VAR, _DEFAULT_TIMEOUT_SECONDS, float)


def _diff_char_limit() -> int:
    """Return the maximum number of characters for the diff."""
    return _parse_positive_env_var(_DIFF_LIMIT_ENV_VAR, _DEFAULT_DIFF_CHAR_LIMIT, int)


def _get_diff(repo_dir: Path, *, base_branch: str) -> str:
    """Get the git diff between the current HEAD and *base_branch*.

    Falls back to ``HEAD~1..HEAD`` if the base-branch comparison fails
    (e.g. shallow clone without the base ref).  Returns empty string if
    git is not installed.
    """
    diff = _run_git_diff(
        repo_dir,
        ["git", "diff", f"{base_branch}...HEAD"],
        not_found_msg=_GIT_NOT_FOUND_DIFF_MSG,
        timeout_label="git diff",
    )
    if diff:
        return diff

    return _run_git_diff(
        repo_dir,
        ["git", "diff", "HEAD~1", "HEAD"],
        not_found_msg=_GIT_NOT_FOUND_DIFF_MSG,
        timeout_label="git diff HEAD~1",
    )


def _run_git_diff(
    repo_dir: Path,
    args: list[str],
    *,
    not_found_msg: str,
    timeout_label: str,
) -> str:
    """Run a ``git diff`` subprocess and return stripped stdout.

    Handles the common pattern of calling ``subprocess.run`` with capture,
    text mode, timeout, and exception handling for missing ``git`` or
    timeouts.

    Args:
        repo_dir: Working directory for the subprocess.
        args: Full argument list (e.g. ``["git", "diff", "--cached"]``).
        not_found_msg: Debug message when ``git`` is not found.
        timeout_label: Human-readable label for timeout warning messages.

    Returns:
        Stripped stdout when the command succeeds, empty string otherwise.
    """
    try:
        result = subprocess.run(
            args,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_DIFF_TIMEOUT_S,
        )
    except FileNotFoundError:
        logger.debug(not_found_msg)
        return ""
    except TimeoutExpired:
        logger.warning("%s timed out after %ss", timeout_label, _GIT_DIFF_TIMEOUT_S)
        return ""
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return ""


def _truncate_diff(diff: str, *, limit: int) -> str:
    """Truncate *diff* to stay within *limit* characters."""
    require_positive_int(limit, "limit")
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
    """Build the prompt that asks the CLI to generate a PR description.

    Raises:
        TypeError: If *diff* or *backend* is not a string.
        ValueError: If *diff* or *backend* is empty/whitespace-only.
    """
    require_non_empty_string(diff, "diff")
    require_non_empty_string(backend, "backend")
    summary_section = ""
    if summary.strip():
        truncated = _truncate_text(summary, limit=_PR_SUMMARY_TRUNCATION_LENGTH)
        summary_section = f"\n## AI Summary of Changes\n{truncated}\n"

    prompt_context = _truncate_text(user_prompt, limit=_PROMPT_CONTEXT_LENGTH)

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
        f"{_PR_TITLE_MARKER} <your title here>\n"
        f"{_PR_BODY_MARKER}\n"
        "<your markdown body here>\n\n"
        f"## Context\n"
        f"- Backend: {backend}\n"
        f"- Original task prompt: {prompt_context}\n"
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
        if line.startswith(_PR_TITLE_MARKER):
            title = line[len(_PR_TITLE_MARKER) :].strip()
        elif line.strip() == _PR_BODY_MARKER:
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
    prompt_as_arg: bool = False,
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
        prompt_as_arg: When ``True``, append the prompt as the last CLI
            argument instead of piping it via stdin.  Used by backends
            that do not read from stdin (e.g. Devin CLI).
    """
    if cmd is None:
        return None

    require_non_empty_string(base_branch, "base_branch")
    require_non_empty_string(backend, "backend")

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

    run_cmd = [*cmd, cli_prompt] if prompt_as_arg else cmd
    stdin_text = None if prompt_as_arg else cli_prompt

    cli_label = cmd[0]
    timeout = _timeout_seconds()
    try:
        result = subprocess.run(
            run_cmd,
            input=stdin_text,
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
        logger.debug(_CLI_NOT_FOUND_MSG + " at execution time.", cli_label)
        return None

    if result.returncode != 0:
        logger.warning(
            "%s PR description generation failed (exit=%d): %s",
            cli_label,
            result.returncode,
            result.stderr.strip()[-_PR_ERROR_TAIL_LENGTH:],
        )
        return None

    parsed = _parse_output(result.stdout)
    if parsed is None:
        logger.warning(
            "Could not parse %s PR description output. Output (last %d chars): %s",
            cli_label,
            _PR_ERROR_TAIL_LENGTH,
            result.stdout.strip()[-_PR_ERROR_TAIL_LENGTH:],
        )
        return None

    logger.info("Generated rich PR description via %s: %s", cli_label, parsed.title)
    return parsed


# ------------------------------------------------------------------
# Commit message generation
# ------------------------------------------------------------------

_COMMIT_MSG_DIFF_LIMIT = 8_000
"""Maximum characters of diff included in the commit message generation prompt."""

_COMMIT_MSG_TIMEOUT = 30.0
"""Timeout in seconds for the CLI commit message generation subprocess."""


def _get_uncommitted_diff(repo_dir: Path) -> str:
    """Get the diff of uncommitted changes (both staged and unstaged).

    Stages all changes first so new files are included, then reads
    ``git diff --cached``.  Returns empty string if git is not installed.
    """
    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            capture_output=True,
            check=False,
            timeout=_GIT_DIFF_TIMEOUT_S,
        )
    except FileNotFoundError:
        logger.debug(_GIT_NOT_FOUND_UNCOMMITTED_MSG)
        return ""
    except TimeoutExpired:
        logger.warning("git add timed out after %ss", _GIT_DIFF_TIMEOUT_S)
        return ""
    return _run_git_diff(
        repo_dir,
        ["git", "diff", "--cached"],
        not_found_msg=_GIT_NOT_FOUND_UNCOMMITTED_MSG,
        timeout_label="git diff --cached",
    )


def _build_commit_message_prompt(
    *,
    diff: str,
    backend: str,
    user_prompt: str,
    summary: str,
) -> str:
    """Build the prompt that asks the CLI to generate a commit message.

    Raises:
        TypeError: If *diff* or *backend* is not a string.
        ValueError: If *diff* or *backend* is empty/whitespace-only.
    """
    require_non_empty_string(diff, "diff")
    require_non_empty_string(backend, "backend")
    summary_section = ""
    if summary.strip():
        truncated = _truncate_text(summary, limit=_COMMIT_SUMMARY_TRUNCATION_LENGTH)
        summary_section = f"\n## AI Summary of Changes\n{truncated}\n"

    prompt_context = _truncate_text(user_prompt, limit=_PROMPT_CONTEXT_LENGTH)

    return (
        "You are generating a git commit message for a code change.\n\n"
        "Instructions:\n"
        "- Write a single-line commit message under 72 characters.\n"
        "- Use conventional commit style (e.g., feat:, fix:, refactor:, docs:, chore:).\n"
        "- Be specific about WHAT changed — do not use generic messages like "
        '"apply updates" or "make changes".\n'
        "- Focus on the purpose/effect of the change, not the mechanism.\n"
        "- Do NOT include a scope in parentheses.\n\n"
        "Output format — reply with ONLY this line, nothing else:\n"
        f"{_COMMIT_MSG_MARKER} <your message here>\n\n"
        f"## Context\n"
        f"- Backend: {backend}\n"
        f"- Original task prompt: {prompt_context}\n"
        f"{summary_section}\n"
        f"## Git Diff\n"
        f"```diff\n{diff}\n```\n"
    )


_MIN_COMMIT_MSG_LENGTH = 8


def _is_trivial_message(msg: str) -> bool:
    """Return True if *msg* is too short or contains only punctuation/filler."""
    # Strip conventional-commit prefix for length check.
    body = _COMMIT_TYPE_PREFIX_RE.sub("", msg)
    # Reject if the body (after prefix) is empty or very short.
    if len(body) < 3:
        return True
    # Reject if body is only punctuation, ellipses, dashes, or whitespace.
    return bool(re.fullmatch(r"[\s\-.,;:!?*/\\#@^&(){}[\]|`~\"']+", body))


def _parse_commit_message(output: str) -> str | None:
    """Extract the commit message from CLI output.

    Returns ``None`` if the output cannot be parsed or the message is
    trivially short / meaningless.
    """
    for line in output.split("\n"):
        if line.startswith(_COMMIT_MSG_MARKER):
            msg = line[len(_COMMIT_MSG_MARKER) :].strip()
            if msg and not _is_trivial_message(msg):
                return msg[:_COMMIT_MSG_MAX_LENGTH]
    return None


_BOILERPLATE_PREFIXES = (
    "Initialization phase:",
    "Execution context:",
    "Repository root:",
    "Repository context learned",
    "Task execution phase",
    "User task request:",
    "Goals:",
    "Indexed files:",
    "Do not ask",
    "Do not perform",
    "Use only tools",
    "If a tool/action",
    "If required write",
    "Implement the task",
    "Follow-up enforcement",
    "Now apply the required",
    "Enabled tools and capabilities:",
    "Skill knowledge catalog:",
)

_BOILERPLATE_PREFIXES_LOWER = tuple(p.lower() for p in _BOILERPLATE_PREFIXES)
"""Pre-lowercased version of :data:`_BOILERPLATE_PREFIXES` to avoid
repeated ``.lower()`` calls inside the hot loop."""


def _is_boilerplate_line(line: str) -> bool:
    """Return True if *line* is CLI banner or hand system boilerplate."""
    # [label] key=value ... banners
    if _BRACKET_BANNER_RE.match(line):
        return True
    # Numbered list items (e.g. "1. Read README.md") and bullet items
    if _NUMBERED_LIST_RE.match(line) or line.startswith("- "):
        return True
    # Known hand-system prompt prefixes echoed by the model
    lower = line.lower()
    return any(lower.startswith(prefix) for prefix in _BOILERPLATE_PREFIXES_LOWER)


def _commit_message_from_prompt(prompt: str, summary: str) -> str:
    """Derive a commit message heuristically from the task prompt or summary.

    Used as a fallback when no CLI tool is available.  When the *summary*
    contains boilerplate/banner lines mixed with real content, the first
    non-boilerplate line is preferred (it describes what was actually done).
    Otherwise the *prompt* (a clean human-written task description) is used.
    """
    # When the summary contains raw CLI output (boilerplate lines), try to
    # extract the first meaningful non-boilerplate line — it describes what
    # was actually done and is more informative than the short prompt.
    first_line = ""
    if summary.strip():
        had_boilerplate = False
        candidate = ""
        for line in summary.strip().split("\n"):
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if _is_boilerplate_line(stripped_line):
                had_boilerplate = True
                continue
            if not candidate:
                candidate = stripped_line
            break
        if had_boilerplate and candidate:
            first_line = candidate

    # Fall back to prompt (always a clean human-written task description),
    # or to the raw summary if prompt is empty.
    if not first_line:
        source = prompt.strip() if prompt.strip() else summary.strip()
        if not source:
            return ""
        first_line = source.split("\n", 1)[0].strip()

    # Split on sentence-ending punctuation followed by a space or end.
    sentence_match = re.match(r"^(.+?[.!?])(?:\s|$)", first_line)
    text = sentence_match.group(1) if sentence_match else first_line

    # Strip leading conventional-commit prefix if already present
    # (with optional parenthetical scope, e.g. "feat(auth): ...").
    stripped = _COMMIT_TYPE_PREFIX_RE.sub("", text)
    text = stripped if stripped else text

    # Lowercase first char, strip trailing period.
    text = text[0].lower() + text[1:] if text else text
    text = text.rstrip(".")

    # Reject trivially short or punctuation-only text.
    commit_type = _infer_commit_type(text)
    if not text or _is_trivial_message(f"{commit_type}: {text}"):
        return ""

    # Assemble with inferred prefix and enforce 72-char limit.
    msg = f"{commit_type}: {text}"
    return msg[:_COMMIT_MSG_MAX_LENGTH]


def generate_commit_message(
    *,
    cmd: list[str] | None,
    repo_dir: Path,
    backend: str,
    prompt: str,
    summary: str,
    prompt_as_arg: bool = False,
) -> str | None:
    """Generate a meaningful commit message using a CLI tool.

    Returns a commit message string, or ``None`` if generation is disabled,
    unavailable, or fails.  The caller should fall back to a default message.

    When *cmd* is ``None`` (no CLI available), falls back to deriving a
    commit message from *prompt* / *summary* heuristically.

    This stages all changes (``git add .``) as a side effect so the diff
    includes new files.  The subsequent ``git commit`` will use the staged
    changes.

    Args:
        prompt_as_arg: When ``True``, append the prompt as the last CLI
            argument instead of piping it via stdin.
    """
    require_non_empty_string(backend, "backend")

    if _is_disabled():
        return None

    if cmd is None:
        msg = _commit_message_from_prompt(prompt, summary)
        if msg:
            logger.info("Generated commit message from prompt: %s", msg)
        return msg or None

    diff = _get_uncommitted_diff(repo_dir)
    if not diff:
        return None

    truncated_diff = _truncate_diff(diff, limit=_COMMIT_MSG_DIFF_LIMIT)

    cli_prompt = _build_commit_message_prompt(
        diff=truncated_diff,
        backend=backend,
        user_prompt=prompt,
        summary=summary,
    )

    run_cmd = [*cmd, cli_prompt] if prompt_as_arg else cmd
    stdin_text = None if prompt_as_arg else cli_prompt

    cli_label = cmd[0]
    try:
        result = subprocess.run(
            run_cmd,
            input=stdin_text,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=_COMMIT_MSG_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "%s commit message generation timed out.",
            cli_label,
        )
        return None
    except FileNotFoundError:
        logger.debug(_CLI_NOT_FOUND_MSG + " for commit message generation.", cli_label)
        return None

    if result.returncode != 0:
        logger.warning(
            "%s commit message generation failed (exit=%d): %s",
            cli_label,
            result.returncode,
            result.stderr.strip()[-_COMMIT_ERROR_TAIL_LENGTH:],
        )
        return None

    msg = _parse_commit_message(result.stdout)
    if msg is None:
        logger.warning(
            "Could not parse %s commit message output: %s",
            cli_label,
            result.stdout.strip()[-_COMMIT_ERROR_TAIL_LENGTH:],
        )
        return None

    logger.info("Generated commit message via %s: %s", cli_label, msg)
    return msg
