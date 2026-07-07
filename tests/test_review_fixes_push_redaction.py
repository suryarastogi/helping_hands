"""Tests that authenticated-push-remote errors never leak the raw token.

``_configure_authenticated_push_remote`` embeds a GitHub token into an https
remote URL. git can echo that URL back in stderr on failure, so the failure
path must run stderr through the credential-redaction helper before it reaches
logs or the raised ``RuntimeError``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.base import Hand

_TOKEN = "ghp_supersecrettoken1234567890abcdef"


@patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
def test_push_remote_failure_redacts_token_in_exception(
    mock_run: MagicMock,
    tmp_path: Path,
) -> None:
    """A failure whose stderr contains the token URL must not leak the token."""
    leaky_stderr = (
        "fatal: unable to access "
        f"'https://x-access-token:{_TOKEN}@github.com/owner/repo.git/': "
        "The requested URL returned error: 403"
    )
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr=leaky_stderr,
    )
    with pytest.raises(RuntimeError) as exc_info:
        Hand._configure_authenticated_push_remote(tmp_path, "owner/repo", _TOKEN)

    message = str(exc_info.value)
    assert _TOKEN not in message
    assert "***" in message
    # The surrounding context is preserved so the error is still actionable.
    assert "403" in message


@patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
def test_push_remote_failure_without_url_still_raises(
    mock_run: MagicMock,
    tmp_path: Path,
) -> None:
    """A failure with no embedded URL is passed through unchanged."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="fatal: no such remote 'origin'",
    )
    with pytest.raises(RuntimeError, match="no such remote"):
        Hand._configure_authenticated_push_remote(tmp_path, "owner/repo", _TOKEN)
