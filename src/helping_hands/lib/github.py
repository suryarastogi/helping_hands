"""GitHub integration: auth, clone, branch, commit, and pull requests.

This module is designed to be used by agents (hands) as a tool/skill.
It wraps PyGithub for the API and subprocess git for local operations.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from github import Auth, Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

logger = logging.getLogger(__name__)


def _redact_sensitive(text: str) -> str:
    """Redact token-bearing GitHub URLs in logs/errors."""
    return re.sub(
        r"(https://x-access-token:)[^@]+(@github\.com/)",
        r"\1***\2",
        text,
    )


def _github_error_message(action: str, exc: GithubException) -> str:
    """Build a clear error message from a PyGithub exception.

    Args:
        action: Human-readable description of what was attempted.
        exc: The caught GithubException.

    Returns:
        An actionable error string including the HTTP status and detail.
    """
    status = getattr(exc, "status", None)
    detail = getattr(exc, "data", {})
    message = ""
    if isinstance(detail, dict):
        message = detail.get("message", "")
    hints: dict[int, str] = {
        401: "check GITHUB_TOKEN is valid and not expired",
        403: "check token permissions or GitHub rate limits",
        404: "resource not found — verify repo name and permissions",
        422: "validation failed — branch may already exist or inputs invalid",
    }
    hint = hints.get(status, "") if status else ""
    parts = [f"GitHub API error: failed to {action}"]
    if status:
        parts.append(f"(HTTP {status})")
    if message:
        parts.append(f"— {message}")
    if hint:
        parts.append(f"[hint: {hint}]")
    return " ".join(parts)


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
        try:
            user = self._gh.get_user()
            return {"login": user.login, "name": user.name, "url": user.html_url}
        except GithubException as exc:
            msg = _github_error_message("authenticate", exc)
            logger.error(msg)
            raise RuntimeError(msg) from exc

    # ------------------------------------------------------------------
    # Repository
    # ------------------------------------------------------------------

    def get_repo(self, full_name: str) -> Repository:
        """Get a repository by owner/name (e.g. ``"suryarastogi/helping_hands"``)."""
        try:
            return self._gh.get_repo(full_name)
        except GithubException as exc:
            msg = _github_error_message(f"access repo '{full_name}'", exc)
            logger.error(msg)
            raise RuntimeError(msg) from exc

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
    def fetch_branch(
        repo_path: Path | str,
        branch_name: str,
        *,
        remote: str = "origin",
    ) -> None:
        """Fetch a remote branch into a matching local branch name."""
        _run_git(
            [
                "git",
                "fetch",
                remote,
                f"refs/heads/{branch_name}:refs/heads/{branch_name}",
            ],
            cwd=repo_path,
        )

    @staticmethod
    def current_branch(repo_path: Path | str) -> str:
        """Return the name of the current branch."""
        result = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        return result.stdout.strip()

    @staticmethod
    def local_branch_exists(repo_path: Path | str, branch_name: str) -> bool:
        """Check whether a local branch exists in the repo."""
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

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

    @staticmethod
    def set_local_identity(
        repo_path: Path | str,
        *,
        name: str,
        email: str,
    ) -> None:
        """Set git author identity in local repo config."""
        _run_git(["git", "config", "user.name", name], cwd=repo_path)
        _run_git(["git", "config", "user.email", email], cwd=repo_path)

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
        try:
            pr: PullRequest = repo.create_pull(
                title=title, body=body, head=head, base=base, draft=draft
            )
        except GithubException as exc:
            msg = _github_error_message(
                f"create PR '{head}' → '{base}' on '{full_name}'", exc
            )
            logger.error(msg)
            raise RuntimeError(msg) from exc
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
        try:
            prs: list[PullRequest] = list(
                repo.get_pulls(state=state, sort="created", direction="desc")
            )[:limit]
        except GithubException as exc:
            msg = _github_error_message(f"list PRs for '{full_name}'", exc)
            logger.error(msg)
            raise RuntimeError(msg) from exc
        return [
            {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
                "head": pr.head.ref,
                "base": pr.base.ref,
            }
            for pr in prs
        ]

    def get_pr(self, full_name: str, number: int) -> dict[str, Any]:
        """Get details of a single pull request."""
        repo = self.get_repo(full_name)
        try:
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
        except GithubException as exc:
            msg = _github_error_message(f"get PR #{number} on '{full_name}'", exc)
            logger.error(msg)
            raise RuntimeError(msg) from exc

    def default_branch(self, full_name: str) -> str:
        """Return the repository's default branch."""
        repo = self.get_repo(full_name)
        return str(repo.default_branch)

    def update_pr_body(self, full_name: str, number: int, *, body: str) -> None:
        """Update the body/description of an existing pull request."""
        repo = self.get_repo(full_name)
        try:
            pr = repo.get_pull(number)
            pr.edit(body=body)
        except GithubException as exc:
            msg = _github_error_message(
                f"update PR #{number} body on '{full_name}'", exc
            )
            logger.error(msg)
            raise RuntimeError(msg) from exc

    def upsert_pr_comment(
        self,
        full_name: str,
        number: int,
        *,
        body: str,
        marker: str = "<!-- helping_hands:status -->",
    ) -> int:
        """Create or update a marker-tagged PR comment.

        If a comment containing ``marker`` already exists, it is edited in place.
        Otherwise, a new comment is created.
        """
        repo = self.get_repo(full_name)
        try:
            issue = repo.get_issue(number=number)
            comment_body = body.rstrip()
            if marker and marker not in comment_body:
                comment_body = f"{comment_body}\n\n{marker}"

            for comment in issue.get_comments():
                existing = comment.body or ""
                if marker and marker in existing:
                    comment.edit(comment_body)
                    return int(comment.id)

            created = issue.create_comment(comment_body)
            return int(created.id)
        except GithubException as exc:
            msg = _github_error_message(
                f"upsert comment on PR #{number} on '{full_name}'", exc
            )
            logger.error(msg)
            raise RuntimeError(msg) from exc

    def find_open_pr_for_branch(
        self,
        full_name: str,
        head_branch: str,
    ) -> PRResult | None:
        """Find an existing open PR with the given head branch.

        Args:
            full_name: ``owner/repo`` string.
            head_branch: Branch name to search for.

        Returns:
            A ``PRResult`` if an open PR exists for the branch, else ``None``.
        """
        try:
            repo = self.get_repo(full_name)
            prs = list(
                repo.get_pulls(state="open", head=f"{repo.owner.login}:{head_branch}")
            )
            if prs:
                pr = prs[0]
                return PRResult(
                    number=pr.number,
                    url=pr.html_url,
                    title=pr.title,
                    head=pr.head.ref,
                    base=pr.base.ref,
                )
        except GithubException as exc:
            logger.warning(
                "Could not check for existing PR on branch '%s': %s",
                head_branch,
                exc,
            )
        return None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying GitHub connection."""
        self._gh.close()

    def __enter__(self) -> GitHubClient:
        """Enter the context manager and return self."""
        return self

    def __exit__(self, *_: Any) -> None:
        """Exit the context manager and close the connection."""
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
        safe_cmd = " ".join(_redact_sensitive(part) for part in cmd)
        safe_stderr = _redact_sensitive(result.stderr.strip())
        msg = f"git failed ({safe_cmd}): {safe_stderr}"
        raise RuntimeError(msg)
    return result
