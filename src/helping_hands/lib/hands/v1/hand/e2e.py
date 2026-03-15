"""End-to-end hand implementation for live repository/PR integration tests.

``E2EHand`` inherits the Hand interface but owns a concrete GitHub workflow
used by CLI ``--e2e`` and app worker task paths: clone, branch, edit, commit,
push, PR create/update, and status-comment refresh.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from helping_hands.lib.config import _TRUTHY_VALUES
from helping_hands.lib.hands.v1.hand.base import _UUID_HEX_LENGTH, Hand, HandResponse

logger = logging.getLogger(__name__)

__all__ = ["E2EHand"]

# --- Module-level constants ---------------------------------------------------

_E2E_MARKER_FILE = "HELPING_HANDS_E2E.md"
"""Filename for the E2E marker file written into cloned repositories."""

_E2E_GIT_USER_NAME = "helping-hands[bot]"
"""Default git user name for E2E commits."""

_E2E_GIT_USER_EMAIL = "helping-hands-bot@users.noreply.github.com"
"""Default git user email for E2E commits."""

_E2E_COMMIT_MESSAGE = "test(e2e): minimal change from E2EHand"
"""Commit message used by E2E hand for marker file changes."""

_E2E_PR_TITLE = "test(e2e): minimal edit by helping_hands"
"""Default PR title for new E2E validation PRs."""

_E2E_STATUS_MARKER = "<!-- helping_hands:e2e-status -->"
"""HTML comment marker used to upsert the E2E status comment on PRs."""


class E2EHand(Hand):
    """Minimal end-to-end hand for validating clone/edit/PR workflow."""

    def __init__(self, config: Any, repo_index: Any) -> None:
        """Initialise the E2E hand.

        Args:
            config: Hand configuration (must include ``repo``).
            repo_index: Repository index instance.
        """
        super().__init__(config, repo_index)

    @staticmethod
    def _safe_repo_dir(repo: str) -> str:
        """Sanitize a repo name for use as a filesystem directory name.

        Replaces non-alphanumeric characters (excluding ``_``, ``.``,
        ``-``) with underscores and strips leading/trailing slashes.

        Args:
            repo: Repository identifier (e.g. ``"owner/repo"``).

        Returns:
            Filesystem-safe directory name string.
        """
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", repo.strip("/"))

    @staticmethod
    def _work_base() -> Path:
        """Return the base working directory for E2E hand workspaces.

        Reads ``HELPING_HANDS_WORK_ROOT`` from the environment, falling
        back to the current directory.

        Returns:
            Expanded :class:`Path` for the work root.
        """
        root = os.environ.get("HELPING_HANDS_WORK_ROOT", ".")
        return Path(root).expanduser()

    @staticmethod
    def _configured_base_branch() -> str:
        """Return the explicitly configured base branch, if any.

        Reads ``HELPING_HANDS_BASE_BRANCH`` from the environment.

        Returns:
            Stripped branch name string, or empty string if not set.
        """
        return os.environ.get("HELPING_HANDS_BASE_BRANCH", "").strip()

    @staticmethod
    def _build_e2e_pr_comment(
        *,
        hand_uuid: str,
        prompt: str,
        stamp_utc: str,
        commit_sha: str,
    ) -> str:
        """Build the markdown body for the E2E status PR comment.

        Args:
            hand_uuid: Unique identifier for this hand invocation.
            prompt: User-supplied task prompt.
            stamp_utc: ISO-8601 UTC timestamp string.
            commit_sha: Git commit SHA of the E2E change.

        Returns:
            Formatted markdown string for the upserted PR comment.
        """
        return (
            "## helping_hands E2E update\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- hand_uuid: `{hand_uuid}`\n"
            f"- commit: `{commit_sha}`\n"
            f"- prompt: {prompt}\n"
        )

    @staticmethod
    def _build_e2e_pr_body(
        *,
        hand_uuid: str,
        prompt: str,
        stamp_utc: str,
        commit_sha: str,
    ) -> str:
        """Build the markdown body for a new E2E validation PR.

        Args:
            hand_uuid: Unique identifier for this hand invocation.
            prompt: User-supplied task prompt.
            stamp_utc: ISO-8601 UTC timestamp string.
            commit_sha: Git commit SHA of the E2E change.

        Returns:
            Formatted markdown string for the PR body.
        """
        return (
            "Automated E2E validation PR.\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- hand_uuid: `{hand_uuid}`\n"
            f"- prompt: {prompt}\n"
            f"- commit: `{commit_sha}`\n"
        )

    @staticmethod
    def _draft_pr_enabled() -> bool:
        """Check whether E2E PRs should be created as drafts."""
        return (
            os.environ.get("HELPING_HANDS_E2E_DRAFT_PR", "true").strip().lower()
            in _TRUTHY_VALUES
        )

    def run(
        self,
        prompt: str,
        hand_uuid: str | None = None,
        pr_number: int | None = None,
        dry_run: bool = False,
    ) -> HandResponse:
        """Execute the full E2E clone/edit/commit/push/PR workflow.

        Clones the target repo, writes a marker file, commits and pushes,
        then creates or updates a PR.  When ``dry_run`` is ``True``,
        skips push and PR creation.

        Args:
            prompt: User-supplied task prompt.
            hand_uuid: Optional hand invocation UUID (auto-generated if
                not provided).
            pr_number: Existing PR number to update, or ``None`` to
                create a new PR.
            dry_run: If ``True``, skip push/PR operations.

        Returns:
            :class:`HandResponse` with metadata about the E2E run.

        Raises:
            ValueError: If ``config.repo`` is empty.
            RuntimeError: If PR number is unexpectedly ``None`` after
                PR creation.
        """
        from helping_hands.lib.github import GitHubClient

        repo = self.config.repo.strip()
        if not repo:
            raise ValueError("E2EHand requires config.repo set to a GitHub owner/repo.")

        hand_uuid = hand_uuid or str(uuid4())
        safe_repo = self._safe_repo_dir(self.config.repo)
        hand_root = self._work_base() / hand_uuid
        repo_dir = hand_root / "git" / safe_repo
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        base_branch = self._configured_base_branch() or "main"
        branch = f"helping-hands/e2e-{hand_uuid[:_UUID_HEX_LENGTH]}"
        e2e_file = _E2E_MARKER_FILE
        e2e_path = repo_dir / e2e_file

        gh_token = getattr(self.config, "github_token", "")
        with GitHubClient(token=gh_token) as gh:
            pr_url = ""
            resumed_pr = False
            pr_info: dict[str, Any] | None = None
            clone_branch = base_branch
            if pr_number is not None:
                pr_info = gh.get_pr(repo, pr_number)
                base_branch = str(pr_info["base"])
                pr_url = str(pr_info["url"])
                clone_branch = base_branch
                if not dry_run:
                    branch = str(pr_info["head"])
                    resumed_pr = True
            elif not self._configured_base_branch():
                try:
                    base_branch = gh.default_branch(repo)
                    clone_branch = base_branch
                except Exception:
                    logger.debug(
                        "Failed to fetch default branch for %s",
                        repo,
                        exc_info=True,
                    )
                    clone_branch = None

            gh.clone(repo, repo_dir, branch=clone_branch, depth=1)
            if clone_branch is None:
                detected = gh.current_branch(repo_dir)
                if detected:
                    base_branch = detected
            repo_dir.mkdir(parents=True, exist_ok=True)
            if resumed_pr:
                gh.fetch_branch(repo_dir, branch)
                gh.switch_branch(repo_dir, branch)
            else:
                gh.create_branch(repo_dir, branch)

            stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
            e2e_path.write_text(
                (
                    "# helping_hands E2E marker\n\n"
                    f"- hand_uuid: `{hand_uuid}`\n"
                    f"- prompt: {prompt}\n"
                    f"- timestamp_utc: {stamp}\n"
                ),
                encoding="utf-8",
            )
            commit_sha = ""
            final_pr_number = pr_number
            if not dry_run:
                git_name = os.environ.get(
                    "HELPING_HANDS_GIT_USER_NAME", _E2E_GIT_USER_NAME
                )
                git_email = os.environ.get(
                    "HELPING_HANDS_GIT_USER_EMAIL",
                    _E2E_GIT_USER_EMAIL,
                )
                gh.set_local_identity(repo_dir, name=git_name, email=git_email)
                commit_sha = gh.add_and_commit(
                    repo_dir,
                    _E2E_COMMIT_MESSAGE,
                    paths=[e2e_file],
                )
                gh.push(repo_dir, branch=branch, set_upstream=True)
                pr_body = self._build_e2e_pr_body(
                    hand_uuid=hand_uuid,
                    prompt=prompt,
                    stamp_utc=stamp,
                    commit_sha=commit_sha,
                )
                if resumed_pr:
                    final_pr_number = pr_number
                else:
                    pr = gh.create_pr(
                        repo,
                        title=_E2E_PR_TITLE,
                        body=pr_body,
                        head=branch,
                        base=base_branch,
                        draft=self._draft_pr_enabled(),
                    )
                    pr_url = pr.url
                    final_pr_number = pr.number
                if final_pr_number is None:
                    raise RuntimeError(
                        "final_pr_number is unexpectedly None after PR creation"
                    )
                gh.update_pr_body(repo, final_pr_number, body=pr_body)
                gh.upsert_pr_comment(
                    repo,
                    final_pr_number,
                    body=self._build_e2e_pr_comment(
                        hand_uuid=hand_uuid,
                        prompt=prompt,
                        stamp_utc=stamp,
                        commit_sha=commit_sha,
                    ),
                    marker=_E2E_STATUS_MARKER,
                )

        if dry_run:
            message = "E2EHand dry run complete. No push/PR performed."
        else:
            message = f"E2EHand complete. PR: {pr_url}"
        return HandResponse(
            message=message,
            metadata={
                "backend": "e2e",
                "model": self.config.model,
                "hand_uuid": hand_uuid,
                "hand_root": str(hand_root),
                "repo": repo,
                "workspace": str(repo_dir),
                "branch": branch,
                "base_branch": base_branch,
                "commit": commit_sha,
                "pr_number": "" if final_pr_number is None else str(final_pr_number),
                "pr_url": pr_url,
                "resumed_pr": str(resumed_pr).lower(),
                "dry_run": str(dry_run).lower(),
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream the E2E hand result as a single message.

        Delegates to :meth:`run` and yields the response message.

        Args:
            prompt: User-supplied task prompt.

        Yields:
            Single string with the E2E run result message.
        """
        yield self.run(prompt).message
