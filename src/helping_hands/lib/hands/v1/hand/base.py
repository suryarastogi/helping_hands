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
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import uuid4

__all__ = ["Hand", "HandResponse"]

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from helping_hands.lib.config import Config
    from helping_hands.lib.repo import RepoIndex


@dataclass
class HandResponse:
    """Standardised response from any Hand backend."""

    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Hand(abc.ABC):
    """Abstract base for all Hand backends."""

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        self.config = config
        self.repo_index = repo_index
        self._interrupt_event = Event()
        self.auto_pr = True

    def _build_system_prompt(self) -> str:
        """Build a system prompt that includes repo context."""
        file_list = "\n".join(f"  - {f}" for f in self.repo_index.files[:200])
        return (
            "You are a helpful coding assistant working on a repository.\n"
            f"Repo root: {self.repo_index.root}\n"
            f"Files ({len(self.repo_index.files)} total):\n{file_list}\n\n"
            "Follow the repo's conventions. Propose focused, reviewable "
            "changes. Explain your reasoning."
        )

    @abc.abstractmethod
    def run(self, prompt: str) -> HandResponse:
        """Send a prompt and get a complete response."""

    @abc.abstractmethod
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Send a prompt and yield response chunks as they arrive."""

    def interrupt(self) -> None:
        """Request cooperative interruption for long-running runs/streams."""
        self._interrupt_event.set()

    def reset_interrupt(self) -> None:
        """Clear any pending interruption request."""
        self._interrupt_event.clear()

    def _is_interrupted(self) -> bool:
        """Return whether cooperative interruption has been requested."""
        return self._interrupt_event.is_set()

    @staticmethod
    def _default_base_branch() -> str:
        """Return the target base branch for PRs (env override or ``main``)."""
        return os.environ.get("HELPING_HANDS_BASE_BRANCH", "main")

    @staticmethod
    def _run_git_read(repo_dir: Path, *args: str) -> str:
        """Run a git command and return stdout, or empty string on failure."""
        result = subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    @classmethod
    def _github_repo_from_origin(cls, repo_dir: Path) -> str:
        """Extract ``owner/repo`` from the git origin URL, or empty string."""
        remote = cls._run_git_read(repo_dir, "remote", "get-url", "origin")
        if not remote:
            return ""

        parsed = urlparse(remote)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme in {"http", "https", "ssh"} and hostname == "github.com":
            repo = parsed.path.lstrip("/")
            if repo.endswith(".git"):
                repo = repo[:-4]
            if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
                return repo

        scp_like = re.match(
            r"^git@github\.com:(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
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
        """Build a fallback PR body when rich description generation is unavailable."""
        return (
            f"Automated update from `{backend}`.\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- prompt: {prompt}\n"
            f"- commit: `{commit_sha}`\n\n"
            "## Summary\n\n"
            f"{summary.strip() or 'No summary provided.'}\n"
        )

    @staticmethod
    def _configure_authenticated_push_remote(
        repo_dir: Path, repo: str, token: str
    ) -> None:
        """Set the push URL to a token-authenticated HTTPS remote."""
        push_url = f"https://x-access-token:{token}@github.com/{repo}.git"
        result = subprocess.run(
            ["git", "remote", "set-url", "--push", "origin", push_url],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown git error"
            msg = f"failed to configure authenticated push remote: {stderr}"
            raise RuntimeError(msg)

    def _use_native_git_auth_for_push(self, *, github_token: str) -> bool:
        """Whether PR push should use the repo's existing git auth setup."""
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
        """Return whether pre-commit hooks should run before PR finalization."""
        return bool(getattr(self.config, "enable_execution", False))

    @staticmethod
    def _run_precommit_checks_and_fixes(repo_dir: Path) -> None:
        """Run pre-commit hooks with one auto-fix retry before PR push.

        Executes ``uv run pre-commit run --all-files`` twice: the first pass
        lets auto-fixers apply corrections, and the second validates. Raises
        ``RuntimeError`` if hooks still fail after the retry.
        """
        command = ["uv", "run", "pre-commit", "run", "--all-files"]

        def _run_once() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
            )

        try:
            first_pass = _run_once()
        except FileNotFoundError as exc:
            msg = (
                "failed to run pre-commit before PR finalization: uv is not available. "
                "Install uv/pre-commit or disable execution tools."
            )
            raise RuntimeError(msg) from exc

        if first_pass.returncode == 0:
            return

        try:
            second_pass = _run_once()
        except FileNotFoundError as exc:
            msg = (
                "failed to run pre-commit before PR finalization: uv is not available. "
                "Install uv/pre-commit or disable execution tools."
            )
            raise RuntimeError(msg) from exc
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
        if len(combined_output) > 4000:
            combined_output = f"{combined_output[:4000]}\n...[truncated]"
        msg = (
            "pre-commit checks failed after an auto-fix retry. "
            "Resolve hook failures locally before PR push.\n"
            f"command: {' '.join(command)}\n"
            f"{combined_output}"
        )
        raise RuntimeError(msg)

    @staticmethod
    def _push_with_non_interactive_env(gh: Any, repo_dir: Path, branch: str) -> None:
        """Push *branch* with git interactive prompts disabled.

        Temporarily sets ``GIT_TERMINAL_PROMPT=0`` and ``GCM_INTERACTIVE=never``
        so that credential helpers never block on stdin, restoring prior values
        in the finally block.
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

    def _create_pr_from_branch(
        self,
        gh: Any,
        *,
        repo: str,
        repo_dir: Path,
        branch: str,
        commit_sha: str,
        backend: str,
        prompt: str,
        summary: str,
    ) -> dict[str, str]:
        """Generate PR title/body and open the pull request.

        Returns a metadata dict with ``pr_status``, ``pr_url``, ``pr_number``,
        ``pr_branch``, and ``pr_commit`` on success.
        """
        base_branch = self._default_base_branch()
        try:
            repo_obj = gh.get_repo(repo)
            if getattr(repo_obj, "default_branch", ""):
                base_branch = str(repo_obj.default_branch)
        except RuntimeError:
            logger.debug(
                "Could not fetch default branch from GitHub for %s",
                repo,
                exc_info=True,
            )

        stamp = datetime.now(UTC).replace(microsecond=0).isoformat()

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
            pr_title = rich_desc.title
            pr_body = rich_desc.body
        else:
            pr_title = f"feat({backend}): automated hand update"
            pr_body = self._build_generic_pr_body(
                backend=backend,
                prompt=prompt,
                summary=summary,
                commit_sha=commit_sha,
                stamp_utc=stamp,
            )

        pr = gh.create_pr(
            repo,
            title=pr_title,
            body=pr_body,
            head=branch,
            base=base_branch,
        )
        return {
            "pr_status": "created",
            "pr_url": pr.url,
            "pr_number": str(pr.number),
            "pr_branch": branch,
            "pr_commit": commit_sha,
        }

    def _finalize_repo_pr(
        self,
        *,
        backend: str,
        prompt: str,
        summary: str,
    ) -> dict[str, str]:
        """Commit, push, and open a PR for any pending repository changes.

        Performs pre-flight checks (auto_pr enabled, repo exists, has changes,
        GitHub origin found), optional pre-commit, then delegates to
        ``_push_with_non_interactive_env`` and ``_create_pr_from_branch``.
        """
        metadata: dict[str, str] = {
            "auto_pr": str(self.auto_pr).lower(),
            "pr_status": "not_attempted",
            "pr_url": "",
            "pr_number": "",
            "pr_branch": "",
            "pr_commit": "",
        }
        if not self.auto_pr:
            metadata["pr_status"] = "disabled"
            return metadata

        repo_dir = self.repo_index.root.resolve()
        if not repo_dir.is_dir():
            metadata["pr_status"] = "no_repo"
            return metadata

        inside_work_tree = self._run_git_read(
            repo_dir, "rev-parse", "--is-inside-work-tree"
        )
        if inside_work_tree != "true":
            metadata["pr_status"] = "not_git_repo"
            return metadata

        has_changes = self._run_git_read(repo_dir, "status", "--porcelain")
        if not has_changes:
            metadata["pr_status"] = "no_changes"
            return metadata

        repo = self._github_repo_from_origin(repo_dir)
        if not repo:
            metadata["pr_status"] = "no_github_origin"
            return metadata

        if self._should_run_precommit_before_pr():
            try:
                self._run_precommit_checks_and_fixes(repo_dir)
            except RuntimeError as exc:
                metadata["pr_status"] = "precommit_failed"
                metadata["pr_error"] = str(exc)
                return metadata
            has_changes = self._run_git_read(repo_dir, "status", "--porcelain")
            if not has_changes:
                metadata["pr_status"] = "no_changes"
                return metadata

        from helping_hands.lib.github import GitHubClient

        try:
            with GitHubClient() as gh:
                git_name = os.environ.get(
                    "HELPING_HANDS_GIT_USER_NAME", "helping-hands[bot]"
                )
                git_email = os.environ.get(
                    "HELPING_HANDS_GIT_USER_EMAIL",
                    "helping-hands-bot@users.noreply.github.com",
                )
                gh.set_local_identity(repo_dir, name=git_name, email=git_email)

                branch = f"helping-hands/{backend}-{uuid4().hex[:8]}"
                gh.create_branch(repo_dir, branch)
                commit_sha = gh.add_and_commit(
                    repo_dir,
                    f"feat({backend}): apply hand updates",
                )
                if not self._use_native_git_auth_for_push(github_token=gh.token):
                    self._configure_authenticated_push_remote(repo_dir, repo, gh.token)
                self._push_with_non_interactive_env(gh, repo_dir, branch)
                pr_meta = self._create_pr_from_branch(
                    gh,
                    repo=repo,
                    repo_dir=repo_dir,
                    branch=branch,
                    commit_sha=commit_sha,
                    backend=backend,
                    prompt=prompt,
                    summary=summary,
                )
                metadata.update(pr_meta)
                return metadata
        except ValueError as exc:
            logger.warning("PR finalization: missing token — %s", exc)
            metadata["pr_status"] = "missing_token"
            metadata["pr_error"] = str(exc)
            return metadata
        except RuntimeError as exc:
            logger.warning("PR finalization: git error — %s", exc)
            metadata["pr_status"] = "git_error"
            metadata["pr_error"] = str(exc)
            return metadata
        except (OSError, KeyError, AttributeError) as exc:
            logger.exception("PR finalization failed")
            metadata["pr_status"] = "error"
            metadata["pr_error"] = str(exc)
            return metadata
