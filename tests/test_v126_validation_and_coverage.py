"""Tests for v126: empty-string inputs are rejected at the API boundary.

An empty repo_path or prompt string passes length checks at zero bytes but produces
nonsensical Celery tasks (no target repo, no instructions).  The min_length=1
constraint must fire before any persistence or worker dispatch so that callers receive
a clear 422 Validation Error rather than a cryptic worker failure buried in logs.

_run_bash_script mutual exclusivity ensures callers cannot supply both a script_path
and an inline_script simultaneously, which would leave ambiguous semantics.

_require_http_url host validation rejects localhost/private URLs from web-facing
tool calls, preventing SSRF when the MCP server is exposed publicly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ===================================================================
# Server request model validation — empty repo_path / prompt
# ===================================================================

pytest.importorskip("fastapi")


class TestBuildRequestMinLength:
    """Validate min_length=1 constraints on BuildRequest fields."""

    def test_rejects_empty_repo_path(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="repo_path"):
            BuildRequest(repo_path="", prompt="do something")

    def test_rejects_empty_prompt(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="prompt"):
            BuildRequest(repo_path="/tmp/repo", prompt="")

    def test_accepts_single_char_repo_path(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/", prompt="test")
        assert req.repo_path == "/"

    def test_accepts_single_char_prompt(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="x")
        assert req.prompt == "x"


class TestScheduleRequestMinLength:
    """Validate min_length=1 constraints on ScheduleRequest fields."""

    def test_rejects_empty_repo_path(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="repo_path"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="",
                prompt="do something",
            )

    def test_rejects_empty_prompt(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="prompt"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="/tmp/repo",
                prompt="",
            )

    def test_accepts_single_char_fields(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="t",
            cron_expression="0 0 * * *",
            repo_path="/",
            prompt="x",
        )
        assert req.repo_path == "/"
        assert req.prompt == "x"


# ===================================================================
# _run_bash_script — mutual exclusivity validation
# ===================================================================


class TestRunBashScriptMutualExclusivity:
    """Validate that exactly one of script_path / inline_script is required."""

    def test_rejects_neither_provided(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.registry import _run_bash_script

        with pytest.raises(ValueError, match="exactly one"):
            _run_bash_script(tmp_path, {})

    def test_rejects_both_provided(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.registry import _run_bash_script

        with pytest.raises(ValueError, match="exactly one"):
            _run_bash_script(
                tmp_path,
                {"script_path": "run.sh", "inline_script": "echo hi"},
            )

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_bash_script")
    def test_accepts_script_path_only(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = MagicMock()
        from helping_hands.lib.meta.tools.registry import _run_bash_script

        _run_bash_script(tmp_path, {"script_path": "run.sh"})
        assert mock_run.call_count == 1

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_bash_script")
    def test_accepts_inline_script_only(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = MagicMock()
        from helping_hands.lib.meta.tools.registry import _run_bash_script

        _run_bash_script(tmp_path, {"inline_script": "echo hi"})
        assert mock_run.call_count == 1


# ===================================================================
# _as_string_keyed_dict — direct tests
# ===================================================================


class TestAsStringKeyedDict:
    """Direct tests for the _as_string_keyed_dict helper."""

    def test_accepts_valid_string_keyed_dict(self) -> None:
        from helping_hands.lib.meta.tools.web import _as_string_keyed_dict

        result = _as_string_keyed_dict({"key": "value", "num": 42})
        assert result == {"key": "value", "num": 42}

    def test_accepts_empty_dict(self) -> None:
        from helping_hands.lib.meta.tools.web import _as_string_keyed_dict

        result = _as_string_keyed_dict({})
        assert result == {}

    def test_rejects_non_dict(self) -> None:
        from helping_hands.lib.meta.tools.web import _as_string_keyed_dict

        assert _as_string_keyed_dict("not a dict") is None
        assert _as_string_keyed_dict(42) is None
        assert _as_string_keyed_dict([1, 2, 3]) is None
        assert _as_string_keyed_dict(None) is None

    def test_rejects_dict_with_non_string_keys(self) -> None:
        from helping_hands.lib.meta.tools.web import _as_string_keyed_dict

        assert _as_string_keyed_dict({1: "value"}) is None
        assert _as_string_keyed_dict({None: "value"}) is None

    def test_rejects_mixed_key_types(self) -> None:
        from helping_hands.lib.meta.tools.web import _as_string_keyed_dict

        assert _as_string_keyed_dict({"valid": 1, 2: "invalid"}) is None


# ===================================================================
# _require_http_url — host validation edge cases
# ===================================================================


class TestRequireHttpUrlHostValidation:
    """Test _require_http_url validates host presence."""

    def test_rejects_http_without_host(self) -> None:
        from helping_hands.lib.meta.tools.web import _require_http_url

        with pytest.raises(ValueError, match="host"):
            _require_http_url("http://")

    def test_rejects_https_without_host(self) -> None:
        from helping_hands.lib.meta.tools.web import _require_http_url

        with pytest.raises(ValueError, match="host"):
            _require_http_url("https://")

    def test_accepts_http_with_host(self) -> None:
        from helping_hands.lib.meta.tools.web import _require_http_url

        result = _require_http_url("http://example.com")
        assert result == "http://example.com"

    def test_accepts_https_with_port(self) -> None:
        from helping_hands.lib.meta.tools.web import _require_http_url

        result = _require_http_url("https://example.com:8080/path")
        assert result == "https://example.com:8080/path"

    def test_strips_whitespace(self) -> None:
        from helping_hands.lib.meta.tools.web import _require_http_url

        result = _require_http_url("  https://example.com  ")
        assert result == "https://example.com"

    def test_rejects_ftp_scheme(self) -> None:
        from helping_hands.lib.meta.tools.web import _require_http_url

        with pytest.raises(ValueError, match="http or https"):
            _require_http_url("ftp://example.com")
