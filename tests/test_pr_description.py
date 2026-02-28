"""Tests for helping_hands.lib.hands.v1.hand.pr_description."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.pr_description import (
    PRDescription,
    _build_prompt,
    _diff_char_limit,
    _get_diff,
    _is_disabled,
    _parse_output,
    _timeout_seconds,
    _truncate_diff,
    generate_pr_description,
)

_SAMPLE_CMD = ["claude", "-p", "--output-format", "text"]

# ---------------------------------------------------------------------------
# _is_disabled
# ---------------------------------------------------------------------------


class TestIsDisabled:
    def test_returns_false_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", raising=False)
        assert _is_disabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", "Yes"])
    def test_returns_true_when_set(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", value)
        assert _is_disabled() is True

    def test_returns_false_for_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "")
        assert _is_disabled() is False

    def test_returns_false_for_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "0")
        assert _is_disabled() is False


# ---------------------------------------------------------------------------
# _timeout_seconds
# ---------------------------------------------------------------------------


class TestTimeoutSeconds:
    def test_returns_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", raising=False)
        assert _timeout_seconds() == 60.0

    def test_respects_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "30.0")
        assert _timeout_seconds() == 30.0

    def test_ignores_invalid_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "not-a-number")
        assert _timeout_seconds() == 60.0

    def test_ignores_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "0")
        assert _timeout_seconds() == 60.0

    def test_ignores_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "-5")
        assert _timeout_seconds() == 60.0


# ---------------------------------------------------------------------------
# _diff_char_limit
# ---------------------------------------------------------------------------


class TestDiffCharLimit:
    def test_returns_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", raising=False)
        assert _diff_char_limit() == 12_000

    def test_respects_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "5000")
        assert _diff_char_limit() == 5000

    def test_ignores_invalid_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "xyz")
        assert _diff_char_limit() == 12_000

    def test_ignores_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "0")
        assert _diff_char_limit() == 12_000


# ---------------------------------------------------------------------------
# _truncate_diff
# ---------------------------------------------------------------------------


class TestTruncateDiff:
    def test_short_diff_unchanged(self) -> None:
        diff = "short diff"
        assert _truncate_diff(diff, limit=100) == diff

    def test_exact_limit_unchanged(self) -> None:
        diff = "a" * 100
        assert _truncate_diff(diff, limit=100) == diff

    def test_long_diff_truncated_with_marker(self) -> None:
        diff = "a" * 200
        result = _truncate_diff(diff, limit=100)
        assert result.startswith("a" * 100)
        assert "truncated" in result
        assert "100 chars omitted" in result


# ---------------------------------------------------------------------------
# _get_diff
# ---------------------------------------------------------------------------


class TestGetDiff:
    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_diff_against_base_branch(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="diff --git a/file.py\n+added line\n"
        )
        result = _get_diff(tmp_path, base_branch="main")
        assert "added line" in result
        mock_run.assert_called_once()
        assert "main...HEAD" in mock_run.call_args[0][0]

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_falls_back_to_head_minus_one(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff fallback\n"
            ),
        ]
        result = _get_diff(tmp_path, base_branch="main")
        assert "diff fallback" in result
        assert mock_run.call_count == 2

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_when_no_diff(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=""
        )
        assert _get_diff(tmp_path, base_branch="main") == ""


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_includes_diff_and_context(self) -> None:
        result = _build_prompt(
            diff="diff content here",
            backend="claudecodecli",
            user_prompt="add feature",
            summary="",
        )
        assert "diff content here" in result
        assert "claudecodecli" in result
        assert "add feature" in result
        assert "PR_TITLE:" in result
        assert "PR_BODY:" in result

    def test_includes_summary_when_provided(self) -> None:
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary="This is a summary of the changes.",
        )
        assert "AI Summary of Changes" in result
        assert "This is a summary of the changes." in result

    def test_omits_summary_section_when_empty(self) -> None:
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary="",
        )
        assert "AI Summary of Changes" not in result

    def test_truncates_long_user_prompt(self) -> None:
        long_prompt = "x" * 1000
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt=long_prompt,
            summary="",
        )
        assert "x" * 500 in result
        assert "x" * 501 not in result


# ---------------------------------------------------------------------------
# _parse_output
# ---------------------------------------------------------------------------


class TestParseOutput:
    def test_valid_output_parsed(self) -> None:
        output = (
            "PR_TITLE: feat: add new authentication module\n"
            "PR_BODY:\n"
            "## Summary\n"
            "Added OAuth2 support.\n"
        )
        result = _parse_output(output)
        assert result is not None
        assert result.title == "feat: add new authentication module"
        assert "OAuth2" in result.body

    def test_missing_title_returns_none(self) -> None:
        output = "PR_BODY:\nSome body content.\n"
        assert _parse_output(output) is None

    def test_missing_body_marker_returns_none(self) -> None:
        output = "PR_TITLE: some title\nJust regular text.\n"
        assert _parse_output(output) is None

    def test_empty_body_returns_none(self) -> None:
        output = "PR_TITLE: some title\nPR_BODY:\n"
        assert _parse_output(output) is None

    def test_extra_content_before_markers_ignored(self) -> None:
        output = (
            "Here is your PR description:\n\n"
            "PR_TITLE: fix: resolve login crash\n"
            "PR_BODY:\n"
            "Fixed the null pointer in login handler.\n"
        )
        result = _parse_output(output)
        assert result is not None
        assert result.title == "fix: resolve login crash"
        assert "null pointer" in result.body

    def test_multiline_body_preserved(self) -> None:
        output = (
            "PR_TITLE: refactor: clean up utils\n"
            "PR_BODY:\n"
            "## Changes\n"
            "\n"
            "- Removed unused imports\n"
            "- Simplified error handling\n"
            "\n"
            "## Notes\n"
            "No breaking changes.\n"
        )
        result = _parse_output(output)
        assert result is not None
        assert "Removed unused imports" in result.body
        assert "No breaking changes" in result.body


# ---------------------------------------------------------------------------
# generate_pr_description
# ---------------------------------------------------------------------------


class TestGeneratePRDescription:
    def _common_kwargs(self, tmp_path: Path) -> dict:
        return {
            "cmd": _SAMPLE_CMD,
            "repo_dir": tmp_path,
            "base_branch": "main",
            "backend": "claudecodecli",
            "prompt": "add feature",
            "summary": "done",
        }

    def test_returns_none_when_cmd_is_none(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["cmd"] = None
        assert generate_pr_description(**kwargs) is None

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=True,
    )
    def test_returns_none_when_disabled(self, _mock: MagicMock, tmp_path: Path) -> None:
        assert generate_pr_description(**self._common_kwargs(tmp_path)) is None

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_none_when_no_diff(
        self, _d: MagicMock, _g: MagicMock, tmp_path: Path
    ) -> None:
        assert generate_pr_description(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_none_on_timeout(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=60)
        assert generate_pr_description(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_none_on_nonzero_exit(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="auth error"
        )
        assert generate_pr_description(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_none_on_unparseable_output(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="just some text without markers", stderr=""
        )
        assert generate_pr_description(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_description_on_success(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                "PR_TITLE: feat: add authentication module\n"
                "PR_BODY:\n"
                "## Summary\n"
                "Added OAuth2 support with token refresh.\n"
            ),
            stderr="",
        )
        result = generate_pr_description(**self._common_kwargs(tmp_path))
        assert result is not None
        assert result.title == "feat: add authentication module"
        assert "OAuth2" in result.body

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_none_on_file_not_found(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = FileNotFoundError("cli not found")
        assert generate_pr_description(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_passes_prompt_via_stdin(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="PR_TITLE: feat: test\nPR_BODY:\nBody.\n",
            stderr="",
        )
        generate_pr_description(**self._common_kwargs(tmp_path))
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("input") is not None
        assert "diff content" in call_kwargs.kwargs["input"]

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_uses_provided_cmd(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="PR_TITLE: feat: test\nPR_BODY:\nBody.\n",
            stderr="",
        )
        kwargs = self._common_kwargs(tmp_path)
        kwargs["cmd"] = ["gemini", "-p"]
        generate_pr_description(**kwargs)
        assert mock_run.call_args[0][0] == ["gemini", "-p"]


# ---------------------------------------------------------------------------
# PRDescription dataclass
# ---------------------------------------------------------------------------


class TestPRDescriptionDataclass:
    def test_frozen(self) -> None:
        desc = PRDescription(title="t", body="b")
        with pytest.raises(AttributeError):
            desc.title = "new"  # type: ignore[misc]

    def test_fields(self) -> None:
        desc = PRDescription(title="my title", body="my body")
        assert desc.title == "my title"
        assert desc.body == "my body"
