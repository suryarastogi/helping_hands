"""Tests for helping_hands.server.token_helpers.

Protects the pure helper functions for token redaction and Claude credential
reading.  These functions were extracted from server/app.py so they can be
tested without the FastAPI/Celery server extras installed.

If redact_token leaks too many characters of a short token, secrets appear
in logs and API responses.  If read_claude_credentials_file fails silently
on a corrupt file, the usage dashboard breaks without a clear error.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from helping_hands.server.token_helpers import (
    REDACT_TOKEN_MIN_PARTIAL_LEN,
    REDACT_TOKEN_PREFIX_LEN,
    REDACT_TOKEN_SUFFIX_LEN,
    get_claude_oauth_token,
    read_claude_credentials_file,
    redact_token,
)

# ---------------------------------------------------------------------------
# redact_token
# ---------------------------------------------------------------------------


class TestRedactToken:
    """Tests for redact_token()."""

    def test_none_returns_none(self) -> None:
        assert redact_token(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert redact_token("") is None

    def test_short_token_fully_masked(self) -> None:
        """Tokens at or below the minimum length are fully masked."""
        short = "a" * REDACT_TOKEN_MIN_PARTIAL_LEN
        assert redact_token(short) == "***"

    def test_boundary_token_fully_masked(self) -> None:
        """Token exactly at boundary length is fully masked."""
        boundary = "x" * REDACT_TOKEN_MIN_PARTIAL_LEN
        assert redact_token(boundary) == "***"

    def test_long_token_shows_prefix_suffix(self) -> None:
        """Tokens longer than minimum show prefix and suffix."""
        token = "abcdefghijklmnopqrstuvwxyz"
        result = redact_token(token)
        assert result is not None
        prefix = token[:REDACT_TOKEN_PREFIX_LEN]
        suffix = token[-REDACT_TOKEN_SUFFIX_LEN:]
        assert result == f"{prefix}***{suffix}"

    def test_one_above_boundary(self) -> None:
        """Token one character above boundary shows prefix/suffix."""
        token = "a" * (REDACT_TOKEN_MIN_PARTIAL_LEN + 1)
        result = redact_token(token)
        assert result is not None
        assert result.startswith("a" * REDACT_TOKEN_PREFIX_LEN)
        assert result.endswith("a" * REDACT_TOKEN_SUFFIX_LEN)
        assert "***" in result

    def test_realistic_github_token(self) -> None:
        """Realistic GitHub token gets properly redacted."""
        token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12345678"
        result = redact_token(token)
        assert result == "ghp_***5678"

    def test_single_char_fully_masked(self) -> None:
        assert redact_token("x") == "***"


# ---------------------------------------------------------------------------
# read_claude_credentials_file
# ---------------------------------------------------------------------------


class TestReadClaudeCredentialsFile:
    """Tests for read_claude_credentials_file()."""

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        """Returns None when credentials file does not exist."""
        with patch.object(Path, "home", return_value=tmp_path):
            assert read_claude_credentials_file() is None

    def test_happy_path(self, tmp_path: Path) -> None:
        """Returns the access token from a valid credentials file."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        creds = {"claudeAiOauth": {"accessToken": "test-token-abc"}}
        (claude_dir / ".credentials.json").write_text(
            json.dumps(creds), encoding="utf-8"
        )
        with patch.object(Path, "home", return_value=tmp_path):
            assert read_claude_credentials_file() == "test-token-abc"

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        """Returns None when the file contains invalid JSON."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / ".credentials.json").write_text("not-json{{{", encoding="utf-8")
        with patch.object(Path, "home", return_value=tmp_path):
            assert read_claude_credentials_file() is None

    def test_missing_oauth_key_returns_none(self, tmp_path: Path) -> None:
        """Returns None when the JSON lacks the expected key structure."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / ".credentials.json").write_text(
            json.dumps({"other": "data"}), encoding="utf-8"
        )
        with patch.object(Path, "home", return_value=tmp_path):
            assert read_claude_credentials_file() is None

    def test_os_error_returns_none(self, tmp_path: Path) -> None:
        """Returns None on OS-level read failures."""
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(Path, "is_file", side_effect=OSError("perm")),
        ):
            assert read_claude_credentials_file() is None


# ---------------------------------------------------------------------------
# get_claude_oauth_token
# ---------------------------------------------------------------------------


class TestGetClaudeOauthToken:
    """Tests for get_claude_oauth_token()."""

    def test_creds_file_hit_returns_early(self, tmp_path: Path) -> None:
        """When credentials file has a token, keychain is not attempted."""
        with patch(
            "helping_hands.server.token_helpers.read_claude_credentials_file",
            return_value="file-token",
        ) as mock_read:
            result = get_claude_oauth_token()
        assert result == "file-token"
        mock_read.assert_called_once()

    def test_keychain_json_credentials(self) -> None:
        """Falls back to keychain and parses JSON credentials."""
        creds_json = json.dumps({"claudeAiOauth": {"accessToken": "keychain-token"}})
        mock_result = SimpleNamespace(returncode=0, stdout=f"  {creds_json}  \n")
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_claude_oauth_token() == "keychain-token"

    def test_keychain_raw_jwt_token(self) -> None:
        """Falls back to raw JWT when keychain value is not valid JSON."""
        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        mock_result = SimpleNamespace(returncode=0, stdout=jwt_token + "\n")
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_claude_oauth_token() == jwt_token

    def test_keychain_non_jwt_non_json_returns_none(self) -> None:
        """Returns None when keychain value is neither JSON nor JWT."""
        mock_result = SimpleNamespace(returncode=0, stdout="random-garbage-value\n")
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_claude_oauth_token() is None

    def test_keychain_nonzero_returncode(self) -> None:
        """Returns None when keychain command fails."""
        mock_result = SimpleNamespace(returncode=44, stdout="")
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_claude_oauth_token() is None

    def test_keychain_empty_stdout(self) -> None:
        """Returns None when keychain returns empty output."""
        mock_result = SimpleNamespace(returncode=0, stdout="   \n")
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_claude_oauth_token() is None

    def test_keychain_subprocess_error(self) -> None:
        """Returns None when security command raises SubprocessError."""
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch(
                "subprocess.run",
                side_effect=subprocess.SubprocessError("timeout"),
            ),
        ):
            assert get_claude_oauth_token() is None

    def test_keychain_os_error(self) -> None:
        """Returns None when security binary is not found."""
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch("subprocess.run", side_effect=FileNotFoundError("security")),
        ):
            assert get_claude_oauth_token() is None

    def test_both_sources_fail(self, tmp_path: Path) -> None:
        """Returns None when both credentials file and keychain fail."""
        with (
            patch(
                "helping_hands.server.token_helpers.read_claude_credentials_file",
                return_value=None,
            ),
            patch(
                "subprocess.run",
                side_effect=FileNotFoundError("no security"),
            ),
        ):
            assert get_claude_oauth_token() is None
