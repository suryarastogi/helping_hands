"""GitHub integration: auth, clone, branch, commit, and pull requests.

This module is designed to be used by agents (hands) as a tool/skill.
It wraps PyGithub for the API and subprocess git for local operations.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from github import Auth, Github
from github.PullRequest import PullRequest
from github.Repository import Repository

logger = logging.getLogger(__name__)


@dataclass
class PRResult:
    """Result of creating a pull request."""

    number: int
    url: str
    title: str
    head: str
    base: str


@dataclass
class GitHubClient:
    """Authenticated GitHub client for repo operations.

    Supports token auth (PAT or fine-grained) and GitHub App installation
    tokens. The token is read from the ``token`` field, or falls back to
    the ``GITHUB_TOKEN`` / ``GH_TOKEN`` environment variable.
    """

    token: str = ""
    _gh: Github = field(init=False, repr=False)

    def __post_init__(self) -> None:
        resolved = self.token or os.environ.get(
            "GITHUB_TOKEN", os.environ.get("GH_TOKEN", "")
        )
        if not resolved:
            msg = (
                "No GitHub token provided. Set GITHUB_TOKEN or GH_TOKEN, "
                "or pass token= explicitly."
            )
            raise ValueError(msg)
        self.token = resolved
        self._gh = Github(auth=Auth.Token(self.token))

    # ------------------------------------------------------------------
    # Auth / identity
    # ------------------------------------------------------------------

    def whoami(self) -> dict[str, Any]:
        """Return the authenticated user's login and name."""
        user = self._gh.get_user()
        return {"login": user.login, "name": user.name, "url": user.html_url}

    # ------------------------------------------------------------------
    # Repository
    # ------------------------------------------------------------------

    def get_repo(self, full_name: str) -> Repository:
        """Get a repository by owner/name (e.g. ``"suryarastogi/helping_hands"``)."""
        return self._gh.get_repo(full_name)

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    def clone(
        self,
        full_name: str,
        dest: Path | str,
        *,
        branch: str | None = None,
        depth: int | None = 1,
    ) -> Path:
        """Clone a repo to *dest* using the authenticated token for HTTPS.

        Args:
            full_name: ``owner/repo`` string.
            dest: Local directory to clone into. Created if it doesn't exist.
            branch: Optional branch to check out.
            depth: Shallow clone depth. ``None`` for full history.

        Returns:
            Path to the cloned repository.
        """
        dest = Path(dest)
        url = f"https://x-access-token:{self.token}@github.com/{full_name}.git"
        cmd: list[str] = ["git", "clone"]
        if depth is not None:
            cmd += ["--depth", str(depth)]
        if branch:
            cmd += ["--branch", branch]
        cmd += [url, str(dest)]
        _run_git(cmd)
        logger.info("Cloned %s → %s", full_name, dest)
        return dest

    # ------------------------------------------------------------------
    # Branch
    # ------------------------------------------------------------------

    @staticmethod
    def create_branch(repo_path: Path | str, branch_name: str) -> None:
        """Create and switch to a new branch in a local repo."""
        _run_git(["git", "checkout", "-b", branch_name], cwd=repo_path)

    @staticmethod
    def switch_branch(repo_path: Path | str, branch_name: str) -> None:
        """Switch to an existing branch."""
        _run_git(["git", "checkout", branch_name], cwd=repo_path)

    @staticmethod
    def current_branch(repo_path: Path | str) -> str:
        """Return the name of the current branch."""
        result = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    @staticmethod
    def add_and_commit(
        repo_path: Path | str,
        message: str,
        *,
        paths: list[str] | None = None,
    ) -> str:
        """Stage files and commit. Returns the commit SHA.

        Args:
            repo_path: Local repo directory.
            message: Commit message.
            paths: Specific paths to ``git add``. Defaults to ``["."]`` (all).

        Returns:
            The short SHA of the new commit.
        """
        targets = paths or ["."]
        _run_git(["git", "add", *targets], cwd=repo_path)
        _run_git(["git", "commit", "-m", message], cwd=repo_path)
        result = _run_git(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Push
    # ------------------------------------------------------------------

    def push(
        self,
        repo_path: Path | str,
        *,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = True,
    ) -> None:
        """Push the current branch to the remote.

        Args:
            repo_path: Local repo directory.
            remote: Remote name.
            branch: Branch to push. Defaults to current branch.
            set_upstream: If True, set the upstream tracking ref.
        """
        branch = branch or self.current_branch(repo_path)
        cmd = ["git", "push"]
        if set_upstream:
            cmd += ["-u", remote, branch]
        else:
            cmd += [remote, branch]
        _run_git(cmd, cwd=repo_path)

    # ------------------------------------------------------------------
    # Pull request
    # ------------------------------------------------------------------

    def create_pr(
        self,
        full_name: str,
        *,
        title: str,
        body: str = "",
        head: str,
        base: str = "main",
        draft: bool = False,
    ) -> PRResult:
        """Create a pull request on GitHub.

        Args:
            full_name: ``owner/repo`` string.
            title: PR title.
            body: PR body (markdown).
            head: Source branch name.
            base: Target branch name.
            draft: Whether to create as a draft PR.

        Returns:
            A ``PRResult`` with the PR number, URL, title, head, and base.
        """
        repo = self.get_repo(full_name)
        pr: PullRequest = repo.create_pull(
            title=title, body=body, head=head, base=base, draft=draft
        )
        logger.info("Created PR #%d: %s", pr.number, pr.html_url)
        return PRResult(
            number=pr.number,
            url=pr.html_url,
            title=pr.title,
            head=head,
            base=base,
        )

    # ------------------------------------------------------------------
    # PR helpers
    # ------------------------------------------------------------------

    def list_prs(
        self,
        full_name: str,
        *,
        state: str = "open",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """List pull requests for a repo.

        Args:
            full_name: ``owner/repo`` string.
            state: ``"open"``, ``"closed"``, or ``"all"``.
            limit: Maximum number of PRs to return.
        """
        repo = self.get_repo(full_name)
        prs = repo.get_pulls(state=state, sort="created", direction="desc")
        return [
            {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
                "head": pr.head.ref,
                "base": pr.base.ref,
            }
            for pr in prs[:limit]
        ]

    def get_pr(self, full_name: str, number: int) -> dict[str, Any]:
        """Get details of a single pull request."""
        repo = self.get_repo(full_name)
        pr = repo.get_pull(number)
        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "url": pr.html_url,
            "state": pr.state,
            "head": pr.head.ref,
            "base": pr.base.ref,
            "mergeable": pr.mergeable,
            "merged": pr.merged,
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying GitHub connection."""
        self._gh.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Git subprocess helper
# ---------------------------------------------------------------------------


def _run_git(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a git command, raising on failure."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git failed ({' '.join(cmd)}): {result.stderr.strip()}"
        raise RuntimeError(msg)
    return result
