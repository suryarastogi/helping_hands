"""Shared hand protocol and cross-backend finalization workflow.

This module defines the core interface used across runtime entry points:
- ``Hand``: abstract contract inherited by all hand implementations.
- ``HandResponse``: common return payload for `run` responses.

It also centralizes git/GitHub finalization helpers used by every backend to
implement the default commit/push/PR behavior, so side-effect semantics remain
consistent regardless of which concrete hand class is selected.
"""

from __future__ import annotations

import abc
import logging
import os
import re
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import uuid4

from github import GithubException

from helping_hands.lib.github_url import (
    GITHUB_HOSTNAME as _GITHUB_HOSTNAME,
)
from helping_hands.lib.github_url import (
    GITHUB_TOKEN_USER as _GITHUB_TOKEN_USER,
)
from helping_hands.lib.meta import skills as system_skills
from helping_hands.lib.meta.tools import registry as tool_registry
from helping_hands.lib.validation import require_non_empty_string

logger = logging.getLogger(__name__)

__all__ = ["Hand", "HandResponse", "PRStatus"]

# --- Module-level constants ---------------------------------------------------

_DEFAULT_BASE_BRANCH = "main"
"""Fallback base branch when ``HELPING_HANDS_BASE_BRANCH`` is not set."""

_DEFAULT_GIT_USER_NAME = "helping-hands[bot]"
"""Default git committer name for PR finalization."""

_DEFAULT_GIT_USER_EMAIL = "helping-hands-bot@users.noreply.github.com"
"""Default git committer email for PR finalization."""

_DEFAULT_CI_WAIT_MINUTES: float = 3.0
"""Default number of minutes to wait between CI check polls."""

_DEFAULT_CI_MAX_RETRIES: int = 3
"""Default maximum number of CI fix retry attempts."""

_BRANCH_PREFIX = "helping-hands/"
"""Prefix for auto-generated branch names."""

_UUID_HEX_LENGTH = 8
"""Number of hex characters from a UUID4 used in branch names."""

_MAX_OUTPUT_DISPLAY_LENGTH = 4000
"""Maximum character length for combined pre-commit output before truncation."""

_FILE_LIST_PREVIEW_LIMIT = 200
"""Maximum number of files shown in the system prompt file list."""

_LOG_TRUNCATION_LENGTH = 200
"""Maximum character length for error messages in log output."""

_GIT_READ_TIMEOUT_S = 30
"""Seconds timeout for lightweight git read subprocesses (e.g. status, remote)."""

_PRECOMMIT_TIMEOUT_S = 300
"""Seconds timeout for ``uv run pre-commit run --all-files`` subprocesses."""

_PRECOMMIT_UV_MISSING_MSG = (
    "failed to run pre-commit before PR finalization: uv is not available. "
    "Install uv/pre-commit or disable execution tools."
)
"""Error message when ``uv`` is not found during pre-commit execution."""

_DEFAULT_GIT_ERROR_MSG = "unknown git error"
"""Fallback message when a git subprocess returns non-zero with empty stderr."""

_GIT_HOOK_FAILURE_MARKERS = (
    "husky -",
    "husky:",
    "lint-staged",
    "pre-commit hook",
    "hook failed",
    "eslint found",
    "eslint:",
    "prettier",
)
"""Lowercased substrings that indicate a git commit failure was caused by a
pre-commit hook (Husky, lint-staged, ESLint, Prettier, etc.)."""

_DEFAULT_COMMIT_MSG_TEMPLATE = "feat({backend}): apply hand updates"
"""Fallback commit message when ``generate_commit_message`` returns empty."""

_DEFAULT_PR_TITLE_TEMPLATE = "feat({backend}): automated hand update"
"""Fallback PR title when ``_commit_message_from_prompt`` returns empty."""


def _utc_stamp() -> str:
    """Return the current UTC time as an ISO-8601 string without microseconds.

    Returns:
        ISO-8601 formatted UTC timestamp, e.g. ``"2026-03-15T12:00:00+00:00"``.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# --- PR status enum -----------------------------------------------------------


class PRStatus(StrEnum):
    """All possible outcomes of the PR finalization step.

    Being a :class:`StrEnum`, each member compares equal to its string value
    (e.g. ``PRStatus.CREATED == "created"``), so serialised metadata dicts
    remain human-readable and backward-compatible.
    """

    CREATED = "created"
    """PR was successfully created in this run."""

    UPDATED = "updated"
    """An existing PR was updated (pushed new commits)."""

    NO_CHANGES = "no_changes"
    """No file changes were detected; PR creation was skipped."""

    DISABLED = "disabled"
    """PR creation was explicitly disabled (``--no-pr``)."""

    NOT_ATTEMPTED = "not_attempted"
    """PR creation was not attempted (e.g. no GitHub remote found)."""

    NO_REPO = "no_repo"
    """Repository directory does not exist."""

    NOT_GIT_REPO = "not_git_repo"
    """Directory is not inside a git work tree."""

    NO_GITHUB_ORIGIN = "no_github_origin"
    """No GitHub remote origin was detected."""

    PRECOMMIT_FAILED = "precommit_failed"
    """Pre-commit hooks failed and could not be auto-fixed."""

    MISSING_TOKEN = "missing_token"
    """GitHub token was missing or invalid."""

    GIT_ERROR = "git_error"
    """A git subprocess returned a non-zero exit code."""

    ERROR = "error"
    """An unexpected error occurred during finalization."""


PR_STATUSES_WITH_URL = frozenset({PRStatus.CREATED, PRStatus.UPDATED})
"""PR status values that indicate a PR URL is available."""

PR_STATUSES_SKIPPED = frozenset({PRStatus.NO_CHANGES, PRStatus.DISABLED})
"""PR status values that indicate finalization was intentionally skipped."""

# Backward-compatible aliases so existing imports keep working.
_PR_STATUS_CREATED = PRStatus.CREATED
_PR_STATUS_UPDATED = PRStatus.UPDATED
_PR_STATUS_NO_CHANGES = PRStatus.NO_CHANGES
_PR_STATUS_DISABLED = PRStatus.DISABLED
_PR_STATUS_NOT_ATTEMPTED = PRStatus.NOT_ATTEMPTED
_PR_STATUSES_WITH_URL = PR_STATUSES_WITH_URL
_PR_STATUSES_SKIPPED = PR_STATUSES_SKIPPED

# --- Metadata dictionary key constants ---------------------------------------
# These are the canonical key names used in the PR/CI metadata dict that flows
# between finalization, CI-fix, and status-reporting code paths.

_META_PR_STATUS = "pr_status"
"""Metadata key for the PR finalization outcome (value is a ``PRStatus``)."""

_META_PR_URL = "pr_url"
"""Metadata key for the URL of the created or updated pull request."""

_META_PR_NUMBER = "pr_number"
"""Metadata key for the PR number as a string."""

_META_PR_BRANCH = "pr_branch"
"""Metadata key for the head branch name of the pull request."""

_META_PR_COMMIT = "pr_commit"
"""Metadata key for the latest commit SHA on the PR branch."""

_META_CI_FIX_STATUS = "ci_fix_status"
"""Metadata key for the CI-fix loop outcome (value is a ``CIFixStatus``)."""

_META_CI_FIX_ATTEMPTS = "ci_fix_attempts"
"""Metadata key for the number of CI-fix attempts as a string."""

_META_CI_FIX_ERROR = "ci_fix_error"
"""Metadata key for the error message from a failed CI-fix loop."""

_META_PR_ERROR = "pr_error"
"""Metadata key for the error message from a failed PR operation."""

if TYPE_CHECKING:
    from helping_hands.lib.config import Config
    from helping_hands.lib.repo import RepoIndex


@dataclass
class HandResponse:
    """Standardised response from any Hand backend.

    Attributes:
        message: Human-readable summary of what the hand accomplished.
        metadata: Arbitrary key-value pairs (e.g. PR URL, commit SHA).
    """

    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Hand(abc.ABC):
    """Abstract base for all Hand backends."""

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        """Initialise the hand with configuration and repository context.

        Resolves the tool categories and skill catalog based on the config,
        and sets default values for PR-related flags.

        Args:
            config: Runtime configuration (model, flags, tokens, etc.).
            repo_index: Pre-built index of the target repository.
        """
        self.config = config
        self.repo_index = repo_index
        self._interrupt_event = Event()
        self.auto_pr = True
        self.pr_number: int | None = None
        self.fix_ci: bool = False
        self.ci_check_wait_minutes: float = _DEFAULT_CI_WAIT_MINUTES
        self.ci_max_retries: int = _DEFAULT_CI_MAX_RETRIES

        # Resolve TOOLS (callable capabilities) — independent axis.
        tool_selection = tool_registry.normalize_tool_selection(
            getattr(self.config, "enabled_tools", ())
        )
        merged_tools = tool_registry.merge_with_legacy_tool_flags(
            tool_selection,
            enable_execution=bool(getattr(self.config, "enable_execution", False)),
            enable_web=bool(getattr(self.config, "enable_web", False)),
        )
        self._selected_tool_categories = tool_registry.resolve_tool_categories(
            merged_tools
        )

        # Resolve SKILLS (knowledge catalog) — independent axis.
        skill_names = system_skills.normalize_skill_selection(
            getattr(self.config, "enabled_skills", ())
        )
        self._selected_skills = system_skills.resolve_skills(skill_names)

    def _build_system_prompt(self) -> str:
        """Build a system prompt that includes repo context.

        Assembles a prompt containing the repo root path, a bounded file
        listing (up to :data:`_FILE_LIST_PREVIEW_LIMIT` entries), and an
        optional reference-repositories section.

        Returns:
            Markdown-formatted system prompt string.
        """
        file_list = "\n".join(
            f"  - {f}" for f in self.repo_index.files[:_FILE_LIST_PREVIEW_LIMIT]
        )
        ref_section = self._build_reference_repos_prompt_section()
        return (
            "You are a helpful coding assistant working on a repository.\n"
            f"Repo root: {self.repo_index.root}\n"
            f"Files ({len(self.repo_index.files)} total):\n{file_list}\n\n"
            "Follow the repo's conventions. Propose focused, reviewable "
            "changes. Explain your reasoning."
            f"{ref_section}"
        )

    def _build_reference_repos_prompt_section(self) -> str:
        """Build a prompt section describing read-only reference repos.

        Iterates over ``self.repo_index.reference_repos`` and lists each
        repo's files (up to :data:`_FILE_LIST_PREVIEW_LIMIT`).  Returns an
        empty string when no reference repos are configured.

        Returns:
            Newline-delimited prompt section, or ``""`` if none.
        """
        if not self.repo_index.reference_repos:
            return ""
        parts: list[str] = ["\n\nReference repositories (read-only, do not modify):"]
        for name, path in self.repo_index.reference_repos:
            parts.append(f"\n- {name} at {path}")
            try:
                ref_files = sorted(
                    str(p.relative_to(path))
                    for p in path.rglob("*")
                    if p.is_file() and ".git" not in p.parts
                )[:_FILE_LIST_PREVIEW_LIMIT]
                for f in ref_files:
                    parts.append(f"    {f}")
            except PermissionError:
                parts.append("    (permission denied)")
        return "\n".join(parts)

    @abc.abstractmethod
    def run(self, prompt: str) -> HandResponse:
        """Send a prompt and get a complete response."""

    @abc.abstractmethod
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Send a prompt and yield response chunks as they arrive."""

    def interrupt(self) -> None:
        """Request cooperative interruption for long-running runs/streams.

        Sets the internal event flag so that implementations checking
        ``_is_interrupted()`` can break out of their processing loop.
        """
        self._interrupt_event.set()

    def reset_interrupt(self) -> None:
        """Clear any pending interruption request.

        Resets the internal event flag so that ``_is_interrupted()`` returns
        False, allowing a new ``run()`` or ``stream()`` cycle.
        """
        self._interrupt_event.clear()

    def _is_interrupted(self) -> bool:
        """Check whether a cooperative interruption has been requested.

        Returns:
            True if ``interrupt()`` has been called since the last
            ``reset_interrupt()``.
        """
        return self._interrupt_event.is_set()

    @staticmethod
    def _default_base_branch() -> str:
        """Return the base branch name for new PRs.

        Reads ``HELPING_HANDS_BASE_BRANCH`` from the environment, falling
        back to ``_DEFAULT_BASE_BRANCH`` (``"main"``).

        Returns:
            Branch name string.
        """
        return os.environ.get("HELPING_HANDS_BASE_BRANCH", _DEFAULT_BASE_BRANCH)

    @staticmethod
    def _run_git_read(repo_dir: Path, *args: str) -> str:
        """Run a read-only git command and return its stripped stdout.

        The subprocess is capped at ``_GIT_READ_TIMEOUT_S`` seconds.  On
        timeout or non-zero exit the method returns an empty string instead
        of raising, making it safe for optional/best-effort git queries.

        Args:
            repo_dir: Working directory for the git subprocess.
            *args: Arguments passed to ``git`` (e.g. ``"status"``,
                ``"--porcelain"``).

        Returns:
            Stripped stdout on success, or ``""`` on timeout/error.
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=_GIT_READ_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "git read timed out after %ds: git %s",
                _GIT_READ_TIMEOUT_S,
                " ".join(args),
            )
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    @classmethod
    def _github_repo_from_origin(cls, repo_dir: Path) -> str:
        """Extract ``owner/repo`` from the git origin remote URL.

        Supports HTTPS, SSH, and SCP-style (``git@github.com:…``) remotes.
        Only GitHub URLs are recognised.

        Args:
            repo_dir: Path to the local git repository.

        Returns:
            ``"owner/repo"`` string, or ``""`` if the origin is not a
            recognised GitHub URL.
        """
        remote = cls._run_git_read(repo_dir, "remote", "get-url", "origin")
        if not remote:
            return ""

        parsed = urlparse(remote)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme in {"http", "https", "ssh"} and hostname == _GITHUB_HOSTNAME:
            repo = parsed.path.lstrip("/")
            if repo.endswith(".git"):
                repo = repo[:-4]
            if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
                return repo

        scp_like = re.match(
            rf"^git@{re.escape(_GITHUB_HOSTNAME)}:(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
            remote,
        )
        if scp_like:
            return scp_like.group("repo")
        return ""

    @staticmethod
    def _build_generic_pr_body(
        *,
        backend: str,
        prompt: str,
        summary: str,
        commit_sha: str,
        stamp_utc: str,
    ) -> str:
        """Build a generic Markdown PR body when no rich description is available.

        Args:
            backend: Hand backend name (e.g. ``"claudecodecli"``).
            prompt: The user-supplied task prompt.
            summary: AI-generated change summary (may be empty).
            commit_sha: Latest commit SHA on the PR branch.
            stamp_utc: ISO-8601 UTC timestamp of the update.

        Returns:
            Markdown string suitable for a GitHub PR body.

        Raises:
            ValueError: If *backend*, *prompt*, *commit_sha*, or
                *stamp_utc* is empty/whitespace.
        """
        require_non_empty_string(backend, "backend")
        require_non_empty_string(prompt, "prompt")
        require_non_empty_string(commit_sha, "commit_sha")
        require_non_empty_string(stamp_utc, "stamp_utc")
        return (
            f"Automated update from `{backend}`.\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- prompt: {prompt}\n"
            f"- commit: `{commit_sha}`\n\n"
            "## Summary\n\n"
            f"{summary.strip() or 'No summary provided.'}\n"
        )

    @staticmethod
    def _pr_result_metadata(
        metadata: dict[str, str],
        *,
        status: PRStatus,
        pr_url: str,
        pr_number: str,
        pr_branch: str,
        pr_commit: str,
    ) -> dict[str, str]:
        """Update *metadata* with the standard PR result fields and return it.

        Args:
            metadata: Mutable metadata dict to update.
            status: PR finalization outcome.
            pr_url: URL of the created/updated PR.
            pr_number: PR number as a string.
            pr_branch: Name of the PR head branch.
            pr_commit: Latest commit SHA on the PR branch.

        Returns:
            The same *metadata* dict, updated in-place.

        Raises:
            ValueError: If any of the string fields is empty or
                whitespace-only.
        """
        require_non_empty_string(pr_url, "pr_url")
        require_non_empty_string(pr_number, "pr_number")
        require_non_empty_string(pr_branch, "pr_branch")
        require_non_empty_string(pr_commit, "pr_commit")
        metadata.update(
            {
                _META_PR_STATUS: status,
                _META_PR_URL: pr_url,
                _META_PR_NUMBER: pr_number,
                _META_PR_BRANCH: pr_branch,
                _META_PR_COMMIT: pr_commit,
            }
        )
        return metadata

    @staticmethod
    def _configure_authenticated_push_remote(
        repo_dir: Path, repo: str, token: str
    ) -> None:
        """Set the git push URL for ``origin`` to use token authentication.

        Rewrites the push URL to
        ``https://x-access-token:<token>@github.com/<repo>.git`` so that
        subsequent ``git push`` calls authenticate without interactive prompts.

        Args:
            repo_dir: Path to the local git repository.
            repo: GitHub ``owner/repo`` identifier.
            token: GitHub access token (PAT or installation token).

        Raises:
            ValueError: If *repo_dir* is not an existing directory, or
                *repo* or *token* is empty/whitespace.
            RuntimeError: If the ``git remote set-url`` command fails or
                times out.
        """
        if not repo_dir.is_dir():
            raise ValueError(f"repo_dir must be an existing directory: {repo_dir}")
        require_non_empty_string(repo, "repo")
        require_non_empty_string(token, "token")
        push_url = f"https://{_GITHUB_TOKEN_USER}:{token}@{_GITHUB_HOSTNAME}/{repo}.git"
        try:
            result = subprocess.run(
                ["git", "remote", "set-url", "--push", "origin", push_url],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=_GIT_READ_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "git remote set-url timed out after %ds",
                _GIT_READ_TIMEOUT_S,
            )
            raise RuntimeError(
                f"git remote set-url timed out after {_GIT_READ_TIMEOUT_S}s"
            ) from None
        if result.returncode != 0:
            stderr = result.stderr.strip() or _DEFAULT_GIT_ERROR_MSG
            msg = f"failed to configure authenticated push remote: {stderr}"
            raise RuntimeError(msg)

    def _use_native_git_auth_for_push(self, *, github_token: str) -> bool:
        """Whether PR push should use the repo's existing git auth setup.

        Returns True only when no explicit GitHub token was provided *and*
        the config's ``use_native_cli_auth`` flag is set, allowing the push
        to use whatever credential helper is already configured in git.

        Args:
            github_token: The resolved GitHub token string.

        Returns:
            True if native git auth should be used instead of token-based
            push URL rewriting.
        """
        if github_token.strip():
            return False
        return bool(getattr(self.config, "use_native_cli_auth", False))

    def _pr_description_cmd(self) -> list[str] | None:
        """Return CLI command for generating a rich PR description.

        Subclasses override this to return a command that accepts a prompt
        via stdin and writes text to stdout (e.g. ``["claude", "-p"]``).
        Return ``None`` to skip rich description and use the generic body.
        """
        return None

    def _should_run_precommit_before_pr(self) -> bool:
        """Whether pre-commit hooks should run before PR finalization.

        Enabled when ``config.enable_execution`` is truthy, since
        pre-commit requires tool execution capabilities (e.g. ``uv``).

        Returns:
            True if pre-commit checks should be run.
        """
        return bool(getattr(self.config, "enable_execution", False))

    @staticmethod
    def _is_git_hook_failure(error_msg: str) -> bool:
        """Return True if a git error looks like a pre-commit hook failure."""
        lowered = error_msg.lower()
        return any(marker in lowered for marker in _GIT_HOOK_FAILURE_MARKERS)

    def _try_fix_git_hook_errors(
        self,
        repo_dir: Path,
        error_output: str,
    ) -> bool:
        """Attempt to fix pre-commit hook errors using the AI backend.

        Override in subclasses that have access to an AI backend CLI.
        Returns True if fixes were applied (files changed), False otherwise.
        """
        return False

    def _add_and_commit_with_hook_retry(
        self,
        gh: Any,
        repo_dir: Path,
        message: str,
    ) -> str:
        """Stage, commit, and retry once if a git hook fails.

        Calls ``gh.add_and_commit`` and, on hook failure, invokes
        ``_try_fix_git_hook_errors`` to let the AI backend fix the issues.
        Returns the commit SHA.
        """
        try:
            return gh.add_and_commit(repo_dir, message)
        except RuntimeError as exc:
            error_msg = str(exc)
            if not self._is_git_hook_failure(error_msg):
                raise

            logger.info(
                "Git hook failure detected, attempting AI-assisted fix: %s",
                error_msg[:_LOG_TRUNCATION_LENGTH],
            )

            if not self._try_fix_git_hook_errors(repo_dir, error_msg):
                raise

            return gh.add_and_commit(repo_dir, message)

    @staticmethod
    def _run_precommit_checks_and_fixes(repo_dir: Path) -> None:
        """Run ``uv run pre-commit run --all-files`` with one auto-fix retry.

        Many pre-commit hooks auto-fix files on the first pass (e.g.
        ``ruff format``).  This method runs pre-commit twice: if the first
        pass fails it runs again to pick up auto-fixes.  If the second
        pass also fails, a ``RuntimeError`` is raised with the combined
        output.

        Args:
            repo_dir: Path to the local git repository.

        Raises:
            RuntimeError: If ``uv`` is not found or if pre-commit fails
                after the auto-fix retry.
        """
        command = ["uv", "run", "pre-commit", "run", "--all-files"]

        def _run_once() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=_PRECOMMIT_TIMEOUT_S,
            )

        try:
            first_pass = _run_once()
        except FileNotFoundError as exc:
            raise RuntimeError(_PRECOMMIT_UV_MISSING_MSG) from exc

        if first_pass.returncode == 0:
            return

        try:
            second_pass = _run_once()
        except FileNotFoundError as exc:
            raise RuntimeError(_PRECOMMIT_UV_MISSING_MSG) from exc
        if second_pass.returncode == 0:
            return

        stdout = second_pass.stdout.strip()
        stderr = second_pass.stderr.strip()
        output_parts: list[str] = []
        if stdout:
            output_parts.append(f"stdout:\n{stdout}")
        if stderr:
            output_parts.append(f"stderr:\n{stderr}")
        combined_output = "\n\n".join(output_parts) or "no output captured"
        if len(combined_output) > _MAX_OUTPUT_DISPLAY_LENGTH:
            combined_output = (
                f"{combined_output[:_MAX_OUTPUT_DISPLAY_LENGTH]}\n...[truncated]"
            )
        msg = (
            "pre-commit checks failed after an auto-fix retry. "
            "Resolve hook failures locally before PR push.\n"
            f"command: {' '.join(command)}\n"
            f"{combined_output}"
        )
        raise RuntimeError(msg)

    @staticmethod
    def _push_noninteractive(
        gh: Any,
        repo_dir: Path,
        branch: str,
    ) -> None:
        """Push a branch with git credential prompts suppressed.

        Temporarily sets ``GIT_TERMINAL_PROMPT=0`` and
        ``GCM_INTERACTIVE=never`` to prevent interactive auth prompts,
        then restores the original environment values after the push.

        Args:
            gh: A :class:`~helping_hands.lib.github.GitHubClient` instance.
            repo_dir: Path to the local git repository.
            branch: Branch name to push with ``--set-upstream``.
        """
        prior_prompt = os.environ.get("GIT_TERMINAL_PROMPT")
        prior_gcm_interactive = os.environ.get("GCM_INTERACTIVE")
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        os.environ["GCM_INTERACTIVE"] = "never"
        try:
            gh.push(repo_dir, branch=branch, set_upstream=True)
        finally:
            if prior_prompt is None:
                os.environ.pop("GIT_TERMINAL_PROMPT", None)
            else:
                os.environ["GIT_TERMINAL_PROMPT"] = prior_prompt
            if prior_gcm_interactive is None:
                os.environ.pop("GCM_INTERACTIVE", None)
            else:
                os.environ["GCM_INTERACTIVE"] = prior_gcm_interactive

    def _push_to_existing_pr(
        self,
        *,
        gh: Any,
        repo: str,
        repo_dir: Path,
        backend: str,
        prompt: str,
        summary: str,
        metadata: dict[str, str],
    ) -> dict[str, str]:
        """Commit and push to an existing PR's branch, updating description if owned.

        If the push fails (e.g. unexpected remote changes), a new PR is created
        against the original PR's base branch, referencing the original PR.
        """
        if self.pr_number is None:
            raise ValueError(
                "pr_number must be set before calling _push_to_existing_pr"
            )

        pr_info = gh.get_pr(repo, self.pr_number)
        branch = str(pr_info["head"])
        base_branch = str(pr_info["base"])
        pr_url = str(pr_info["url"])

        from helping_hands.lib.hands.v1.hand.pr_description import (
            generate_commit_message,
        )

        commit_msg = generate_commit_message(
            cmd=self._pr_description_cmd(),
            repo_dir=repo_dir,
            backend=backend,
            prompt=prompt,
            summary=summary,
        ) or _DEFAULT_COMMIT_MSG_TEMPLATE.format(backend=backend)

        commit_sha = self._add_and_commit_with_hook_retry(
            gh,
            repo_dir,
            commit_msg,
        )

        try:
            self._push_noninteractive(gh, repo_dir, branch)
        except RuntimeError as push_exc:
            # Branch diverged or push rejected — create a PR targeting the
            # original PR branch instead.
            logger.warning(
                "Push to PR #%s branch %r failed: %s. "
                "Falling back to diverged-branch PR.",
                self.pr_number,
                branch,
                push_exc,
            )
            return self._create_pr_for_diverged_branch(
                gh=gh,
                repo=repo,
                repo_dir=repo_dir,
                backend=backend,
                prompt=prompt,
                summary=summary,
                metadata=metadata,
                pr_branch=branch,
                commit_sha=commit_sha,
            )

        # Push succeeded — update PR description if the PR was created by us.
        pr_creator = str(pr_info.get("user", ""))
        try:
            token_user = gh.whoami().get("login", "")
        except (GithubException, OSError):
            logger.debug(
                "whoami() failed; skipping PR description update", exc_info=True
            )
            token_user = ""
        if pr_creator and token_user and pr_creator == token_user:
            self._update_pr_description(
                gh=gh,
                repo=repo,
                repo_dir=repo_dir,
                backend=backend,
                prompt=prompt,
                summary=summary,
                base_branch=base_branch,
                commit_sha=commit_sha,
            )

        return self._pr_result_metadata(
            metadata,
            status=PRStatus.UPDATED,
            pr_url=pr_url,
            pr_number=str(self.pr_number),
            pr_branch=branch,
            pr_commit=commit_sha,
        )

    def _generate_pr_title_and_body(
        self,
        *,
        repo_dir: Path,
        base_branch: str,
        backend: str,
        prompt: str,
        summary: str,
        commit_sha: str,
    ) -> tuple[str, str]:
        """Generate a PR title and body, falling back to generic templates.

        Attempts to produce a rich description via the external
        ``generate_pr_description`` helper.  When that returns *None*
        (e.g. the helper binary is unavailable), the method falls back to
        ``_commit_message_from_prompt`` for the title and
        ``_build_generic_pr_body`` for the body.

        Args:
            repo_dir: Absolute path to the repository working directory.
            base_branch: Branch the PR will target.
            backend: Hand backend name for metadata.
            prompt: The original user-supplied task prompt.
            summary: AI-generated change summary.
            commit_sha: Commit SHA to embed in the generic body.

        Returns:
            A ``(title, body)`` tuple.
        """
        from helping_hands.lib.hands.v1.hand.pr_description import (
            generate_pr_description,
        )

        rich_desc = generate_pr_description(
            cmd=self._pr_description_cmd(),
            repo_dir=repo_dir,
            base_branch=base_branch,
            backend=backend,
            prompt=prompt,
            summary=summary,
        )
        if rich_desc is not None:
            return rich_desc.title, rich_desc.body

        from helping_hands.lib.hands.v1.hand.pr_description import (
            _commit_message_from_prompt,
        )

        pr_title = _commit_message_from_prompt(
            prompt, summary
        ) or _DEFAULT_PR_TITLE_TEMPLATE.format(backend=backend)
        stamp = _utc_stamp()
        pr_body = self._build_generic_pr_body(
            backend=backend,
            prompt=prompt,
            summary=summary,
            commit_sha=commit_sha,
            stamp_utc=stamp,
        )
        return pr_title, pr_body

    def _update_pr_description(
        self,
        *,
        gh: Any,
        repo: str,
        repo_dir: Path,
        backend: str,
        prompt: str,
        summary: str,
        base_branch: str,
        commit_sha: str,
    ) -> None:
        """Generate and update the PR description for an owned PR."""
        if self.pr_number is None:
            raise ValueError(
                "pr_number must be set before calling _update_pr_description"
            )
        _, pr_body = self._generate_pr_title_and_body(
            repo_dir=repo_dir,
            base_branch=base_branch,
            backend=backend,
            prompt=prompt,
            summary=summary,
            commit_sha=commit_sha,
        )
        try:
            gh.update_pr_body(repo, self.pr_number, body=pr_body)
        except (GithubException, OSError):
            logger.debug(
                "Failed to update PR #%s description", self.pr_number, exc_info=True
            )

    def _create_pr_for_diverged_branch(
        self,
        *,
        gh: Any,
        repo: str,
        repo_dir: Path,
        backend: str,
        prompt: str,
        summary: str,
        metadata: dict[str, str],
        pr_branch: str,
        commit_sha: str,
    ) -> dict[str, str]:
        """Create a PR-of-PR when push to the original PR branch was rejected.

        The new PR targets the original PR's head branch so it can be merged
        into the existing PR rather than going directly to the base branch.
        """
        if self.pr_number is None:
            raise ValueError(
                "pr_number must be set before calling _create_pr_for_diverged_branch"
            )
        new_branch = f"{_BRANCH_PREFIX}{backend}-{uuid4().hex[:_UUID_HEX_LENGTH]}"
        gh.create_branch(repo_dir, new_branch)
        self._push_noninteractive(gh, repo_dir, new_branch)

        pr_title, pr_body = self._generate_pr_title_and_body(
            repo_dir=repo_dir,
            base_branch=pr_branch,
            backend=backend,
            prompt=prompt,
            summary=summary,
            commit_sha=commit_sha,
        )
        pr_body += f"\n\n---\nFollow-up to #{self.pr_number}."

        pr = gh.create_pr(
            repo,
            title=pr_title,
            body=pr_body,
            head=new_branch,
            base=pr_branch,
        )
        return self._pr_result_metadata(
            metadata,
            status=PRStatus.CREATED,
            pr_url=pr.url,
            pr_number=str(pr.number),
            pr_branch=new_branch,
            pr_commit=commit_sha,
        )

    def _create_new_pr(
        self,
        *,
        gh: Any,
        repo: str,
        repo_dir: Path,
        backend: str,
        prompt: str,
        summary: str,
        metadata: dict[str, str],
    ) -> dict[str, str]:
        """Create a new branch, commit, push, and open a pull request.

        This is the "happy path" for first-time PR creation when no existing
        PR is being updated.  Branch naming, commit message generation, and
        PR description generation are all handled here.

        Args:
            gh: Authenticated :class:`GitHubClient` instance.
            repo: ``"owner/repo"`` string.
            repo_dir: Absolute path to the repository working directory.
            backend: Hand backend name for PR metadata.
            prompt: The original user-supplied task prompt.
            summary: AI-generated change summary.
            metadata: Mutable metadata dict to populate with PR results.

        Returns:
            Updated *metadata* dict with PR status, URL, number, branch,
            and commit SHA.
        """
        branch = f"{_BRANCH_PREFIX}{backend}-{uuid4().hex[:_UUID_HEX_LENGTH]}"
        gh.create_branch(repo_dir, branch)

        from helping_hands.lib.hands.v1.hand.pr_description import (
            generate_commit_message,
        )

        commit_msg = generate_commit_message(
            cmd=self._pr_description_cmd(),
            repo_dir=repo_dir,
            backend=backend,
            prompt=prompt,
            summary=summary,
        ) or _DEFAULT_COMMIT_MSG_TEMPLATE.format(backend=backend)

        commit_sha = self._add_and_commit_with_hook_retry(
            gh,
            repo_dir,
            commit_msg,
        )
        self._push_noninteractive(gh, repo_dir, branch)

        base_branch = self._default_base_branch()
        try:
            repo_obj = gh.get_repo(repo)
            if getattr(repo_obj, "default_branch", ""):
                base_branch = str(repo_obj.default_branch)
        except (GithubException, OSError):
            logger.debug(
                "could not fetch default branch for %s, using %r",
                repo,
                base_branch,
                exc_info=True,
            )

        pr_title, pr_body = self._generate_pr_title_and_body(
            repo_dir=repo_dir,
            base_branch=base_branch,
            backend=backend,
            prompt=prompt,
            summary=summary,
            commit_sha=commit_sha,
        )

        pr = gh.create_pr(
            repo,
            title=pr_title,
            body=pr_body,
            head=branch,
            base=base_branch,
        )
        return self._pr_result_metadata(
            metadata,
            status=PRStatus.CREATED,
            pr_url=pr.url,
            pr_number=str(pr.number),
            pr_branch=branch,
            pr_commit=commit_sha,
        )

    def _validate_finalization_preconditions(
        self,
        metadata: dict[str, str],
    ) -> tuple[Path, str] | None:
        """Check repo-level preconditions before PR finalization.

        Validates that: auto-PR is enabled, the repository directory exists
        and is a git work tree, uncommitted changes are present, a GitHub
        remote origin is detected, and pre-commit hooks (if configured) pass.

        Args:
            metadata: Mutable metadata dict — updated in-place with the
                appropriate ``pr_status`` when a precondition fails.

        Returns:
            A ``(repo_dir, repo_full_name)`` tuple when all preconditions
            pass, or ``None`` when a precondition fails (``metadata`` will
            already contain the failure status).
        """
        if not self.auto_pr:
            metadata[_META_PR_STATUS] = _PR_STATUS_DISABLED
            return None

        repo_dir = self.repo_index.root.resolve()
        if not repo_dir.is_dir():
            metadata[_META_PR_STATUS] = PRStatus.NO_REPO
            return None

        inside_work_tree = self._run_git_read(
            repo_dir, "rev-parse", "--is-inside-work-tree"
        )
        if inside_work_tree != "true":
            metadata[_META_PR_STATUS] = PRStatus.NOT_GIT_REPO
            return None

        has_changes = self._run_git_read(repo_dir, "status", "--porcelain")
        if not has_changes:
            metadata[_META_PR_STATUS] = _PR_STATUS_NO_CHANGES
            return None

        repo = self._github_repo_from_origin(repo_dir)
        if not repo:
            metadata[_META_PR_STATUS] = PRStatus.NO_GITHUB_ORIGIN
            return None

        if self._should_run_precommit_before_pr():
            try:
                self._run_precommit_checks_and_fixes(repo_dir)
            except RuntimeError as exc:
                metadata[_META_PR_STATUS] = PRStatus.PRECOMMIT_FAILED
                metadata[_META_PR_ERROR] = str(exc)
                return None
            has_changes = self._run_git_read(repo_dir, "status", "--porcelain")
            if not has_changes:
                metadata[_META_PR_STATUS] = _PR_STATUS_NO_CHANGES
                return None

        return repo_dir, repo

    def _finalize_repo_pr(
        self,
        *,
        backend: str,
        prompt: str,
        summary: str,
    ) -> dict[str, str]:
        """Commit changes, push, and open (or update) a GitHub pull request.

        This is the main finalization entry point called by hand
        implementations after the AI backend has finished editing files.
        It handles branch creation, commit message generation, push, and
        PR creation/update.  When ``self.pr_number`` is set, changes are
        pushed to the existing PR's branch instead of creating a new one.

        Args:
            backend: Hand backend name for PR metadata.
            prompt: The original user-supplied task prompt.
            summary: AI-generated change summary.

        Returns:
            Metadata dict with keys ``pr_status``, ``pr_url``,
            ``pr_number``, ``pr_branch``, ``pr_commit``, and
            ``auto_pr``.

        Raises:
            ValueError: If *backend* or *prompt* is empty or
                whitespace-only.
        """
        require_non_empty_string(backend, "backend")
        require_non_empty_string(prompt, "prompt")
        metadata = {
            "auto_pr": str(self.auto_pr).lower(),
            _META_PR_STATUS: _PR_STATUS_NOT_ATTEMPTED,
            _META_PR_URL: "",
            _META_PR_NUMBER: "",
            _META_PR_BRANCH: "",
            _META_PR_COMMIT: "",
        }

        result = self._validate_finalization_preconditions(metadata)
        if result is None:
            return metadata
        repo_dir, repo = result

        from helping_hands.lib.github import GitHubClient

        try:
            gh_token = getattr(self.config, "github_token", "")
            with GitHubClient(token=gh_token) as gh:
                git_name = os.environ.get(
                    "HELPING_HANDS_GIT_USER_NAME", _DEFAULT_GIT_USER_NAME
                )
                git_email = os.environ.get(
                    "HELPING_HANDS_GIT_USER_EMAIL",
                    _DEFAULT_GIT_USER_EMAIL,
                )
                gh.set_local_identity(repo_dir, name=git_name, email=git_email)

                if not self._use_native_git_auth_for_push(github_token=gh.token):
                    self._configure_authenticated_push_remote(repo_dir, repo, gh.token)

                if self.pr_number is not None:
                    return self._push_to_existing_pr(
                        gh=gh,
                        repo=repo,
                        repo_dir=repo_dir,
                        backend=backend,
                        prompt=prompt,
                        summary=summary,
                        metadata=metadata,
                    )

                return self._create_new_pr(
                    gh=gh,
                    repo=repo,
                    repo_dir=repo_dir,
                    backend=backend,
                    prompt=prompt,
                    summary=summary,
                    metadata=metadata,
                )
        except ValueError as exc:
            metadata[_META_PR_STATUS] = PRStatus.MISSING_TOKEN
            metadata[_META_PR_ERROR] = str(exc)
            return metadata
        except RuntimeError as exc:
            metadata[_META_PR_STATUS] = PRStatus.GIT_ERROR
            metadata[_META_PR_ERROR] = str(exc)
            return metadata
        except (GithubException, OSError) as exc:
            logger.debug("_finalize_repo_pr unexpected error", exc_info=True)
            metadata[_META_PR_STATUS] = PRStatus.ERROR
            metadata[_META_PR_ERROR] = str(exc)
            return metadata
