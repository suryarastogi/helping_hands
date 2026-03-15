"""Tests for helping_hands.lib.hands.v1.hand.pr_description."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.pr_description import (
    _BRACKET_BANNER_RE,
    _COMMIT_MSG_DIFF_LIMIT,
    _COMMIT_MSG_MARKER,
    _COMMIT_MSG_TIMEOUT,
    _COMMIT_SUMMARY_TRUNCATION_LENGTH,
    _COMMIT_TYPE_KEYWORDS,
    _COMMIT_TYPE_PREFIX_RE,
    _MIN_COMMIT_MSG_LENGTH,
    _NUMBERED_LIST_RE,
    _PR_BODY_MARKER,
    _PR_SUMMARY_TRUNCATION_LENGTH,
    _PR_TITLE_MARKER,
    _PROMPT_CONTEXT_LENGTH,
    PRDescription,
    _build_commit_message_prompt,
    _build_prompt,
    _commit_message_from_prompt,
    _diff_char_limit,
    _get_diff,
    _get_uncommitted_diff,
    _infer_commit_type,
    _is_disabled,
    _is_trivial_message,
    _parse_commit_message,
    _parse_output,
    _timeout_seconds,
    _truncate_diff,
    _truncate_text,
    generate_commit_message,
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

    @pytest.mark.parametrize("value", ["1", "true", "yes", "TRUE", "Yes"])
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

    def test_warns_on_invalid_env(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "abc")
        with caplog.at_level("WARNING"):
            _timeout_seconds()
        assert "non-numeric" in caplog.text
        assert "abc" in caplog.text

    def test_ignores_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "0")
        assert _timeout_seconds() == 60.0

    def test_ignores_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "-5")
        assert _timeout_seconds() == 60.0

    def test_warns_on_negative_env(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_TIMEOUT", "-10")
        with caplog.at_level("WARNING"):
            _timeout_seconds()
        assert "non-positive" in caplog.text
        assert "-10" in caplog.text


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

    def test_warns_on_invalid_env(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "abc")
        with caplog.at_level("WARNING"):
            _diff_char_limit()
        assert "non-numeric" in caplog.text
        assert "abc" in caplog.text

    def test_ignores_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "0")
        assert _diff_char_limit() == 12_000

    def test_ignores_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "-100")
        assert _diff_char_limit() == 12_000

    def test_warns_on_negative_env(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "-50")
        with caplog.at_level("WARNING"):
            _diff_char_limit()
        assert "non-positive" in caplog.text
        assert "-50" in caplog.text


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

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_when_base_branch_success_but_empty_stdout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Base branch diff succeeds (rc=0) but has empty/whitespace stdout."""
        mock_run.side_effect = [
            # base branch diff returns 0 but empty
            subprocess.CompletedProcess(args=[], returncode=0, stdout="   \n"),
            # fallback also returns 0 but empty
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
        ]
        assert _get_diff(tmp_path, base_branch="main") == ""
        assert mock_run.call_count == 2

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_when_git_not_found(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Returns empty string when git is not installed."""
        mock_run.side_effect = FileNotFoundError("git not found")
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

    def test_truncates_long_summary_to_2000_chars(self) -> None:
        long_summary = "s" * 3000
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary=long_summary,
        )
        assert "AI Summary of Changes" in result
        assert "s" * 2000 in result
        assert "s" * 2001 not in result


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

    def test_whitespace_only_body_returns_none(self) -> None:
        output = "PR_TITLE: some title\nPR_BODY:\n   \n  \n"
        assert _parse_output(output) is None

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


# ===========================================================================
# Commit message generation tests
# ===========================================================================


# ---------------------------------------------------------------------------
# _get_uncommitted_diff
# ---------------------------------------------------------------------------


class TestGetUncommittedDiff:
    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_stages_and_returns_cached_diff(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = [
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git diff --cached
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/f.py\n+new line\n"
            ),
        ]
        result = _get_uncommitted_diff(tmp_path)
        assert "new line" in result
        assert mock_run.call_count == 2

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_when_no_diff(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        assert _get_uncommitted_diff(tmp_path) == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_when_git_not_found(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Returns empty string when git is not installed."""
        mock_run.side_effect = FileNotFoundError("git not found")
        assert _get_uncommitted_diff(tmp_path) == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_when_git_diff_cached_not_found(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """git add succeeds but git diff --cached raises FileNotFoundError."""
        mock_run.side_effect = [
            # git add . — succeeds
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git diff --cached — git disappears
            FileNotFoundError("git not found"),
        ]
        assert _get_uncommitted_diff(tmp_path) == ""


# ---------------------------------------------------------------------------
# _build_commit_message_prompt
# ---------------------------------------------------------------------------


class TestBuildCommitMessagePrompt:
    def test_includes_diff_and_context(self) -> None:
        result = _build_commit_message_prompt(
            diff="diff content here",
            backend="claudecodecli",
            user_prompt="add login feature",
            summary="",
        )
        assert "diff content here" in result
        assert "claudecodecli" in result
        assert "add login feature" in result
        assert "COMMIT_MSG:" in result

    def test_includes_summary_when_provided(self) -> None:
        result = _build_commit_message_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary="Added auth module with JWT support.",
        )
        assert "AI Summary of Changes" in result
        assert "Added auth module with JWT support." in result

    def test_omits_summary_when_empty(self) -> None:
        result = _build_commit_message_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary="",
        )
        assert "AI Summary of Changes" not in result

    def test_truncates_long_summary_to_1000_chars(self) -> None:
        long_summary = "c" * 2000
        result = _build_commit_message_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary=long_summary,
        )
        assert "AI Summary of Changes" in result
        assert "c" * 1000 in result
        assert "c" * 1001 not in result


# ---------------------------------------------------------------------------
# _parse_commit_message
# ---------------------------------------------------------------------------


class TestParseCommitMessage:
    def test_valid_output(self) -> None:
        assert (
            _parse_commit_message("COMMIT_MSG: feat: add user authentication")
            == "feat: add user authentication"
        )

    def test_with_extra_lines(self) -> None:
        output = (
            "Here is the message:\n\nCOMMIT_MSG: fix: resolve null pointer in login\n"
        )
        assert _parse_commit_message(output) == "fix: resolve null pointer in login"

    def test_returns_none_for_missing_marker(self) -> None:
        assert _parse_commit_message("just some text") is None

    def test_returns_none_for_empty_message(self) -> None:
        assert _parse_commit_message("COMMIT_MSG: ") is None

    def test_truncates_to_72_chars(self) -> None:
        long_msg = "feat: " + "x" * 100
        result = _parse_commit_message(f"COMMIT_MSG: {long_msg}")
        assert result is not None
        assert len(result) == 72


# ---------------------------------------------------------------------------
# generate_commit_message
# ---------------------------------------------------------------------------


class TestCommitMessageFromPrompt:
    def test_uses_prompt_over_summary(self) -> None:
        result = _commit_message_from_prompt("add login", "Added OAuth2 login flow")
        assert "add login" in result

    def test_falls_back_to_summary_when_prompt_empty(self) -> None:
        result = _commit_message_from_prompt("", "Added OAuth2 login flow")
        assert "added OAuth2 login flow" in result

    def test_returns_empty_when_both_empty(self) -> None:
        assert _commit_message_from_prompt("", "") == ""

    def test_whitespace_only_summary_falls_back_to_prompt(self) -> None:
        result = _commit_message_from_prompt("add user auth", "   \n  ")
        assert "add user auth" in result

    def test_whitespace_only_both_returns_empty(self) -> None:
        assert _commit_message_from_prompt("  ", "  ") == ""

    def test_takes_first_sentence(self) -> None:
        result = _commit_message_from_prompt(
            "Fix the login crash. Also clean up utils.", ""
        )
        assert "fix the login crash" in result
        assert "clean up" not in result

    def test_takes_first_line(self) -> None:
        result = _commit_message_from_prompt(
            "Add new endpoint\nAlso refactor the router", ""
        )
        assert "add new endpoint" in result
        assert "refactor" not in result

    def test_strips_existing_prefix(self) -> None:
        result = _commit_message_from_prompt("feat: add new button", "")
        assert result == "feat: add new button"
        assert not result.startswith("feat: feat:")

    def test_ignores_metadata_summary(self) -> None:
        result = _commit_message_from_prompt(
            "add dark mode toggle",
            "[claudecodecli] isolation=workspace-write | auth=native-cli",
        )
        assert "add dark mode toggle" in result
        assert "claudecodecli" not in result

    def test_enforces_72_char_limit(self) -> None:
        long_prompt = "x" * 200
        result = _commit_message_from_prompt(long_prompt, "")
        assert len(result) <= 72

    def test_starts_with_conventional_prefix(self) -> None:
        result = _commit_message_from_prompt("add dark mode toggle", "")
        assert result.startswith("feat: ")

    def test_skips_cli_banner_lines_in_summary(self) -> None:
        summary = (
            "[claudecodecli] isolation=workspace-write | auth=native-cli "
            "(no ANTHROPIC_API_KEY set, using CLI session)\n"
            "[claudecodecli] [phase 1/2] Initializing repository context...\n"
            "[claudecodecli] [phase 2/2] Executing user task...\n"
            "Added OAuth2 login flow with token refresh."
        )
        result = _commit_message_from_prompt("add login", summary)
        assert "added OAuth2 login flow" in result
        assert "claudecodecli" not in result
        assert "isolation=" not in result

    def test_falls_back_to_prompt_when_summary_is_all_banners(self) -> None:
        summary = (
            "[claudecodecli] isolation=workspace-write | auth=native-cli\n"
            "[claudecodecli] [phase 1/2] Initializing...\n"
        )
        result = _commit_message_from_prompt("add dark mode toggle", summary)
        assert "add dark mode toggle" in result
        assert "claudecodecli" not in result

    def test_skips_echoed_hand_prompt_boilerplate(self) -> None:
        summary = (
            "Execution context: this hand is running inside a non-interactive "
            "helping_hands script started by the user.\n"
            "Repository root: /tmp/repo\n"
            "Goals:\n"
            "1. Read README.md\n"
            "Added a new authentication endpoint with JWT support."
        )
        result = _commit_message_from_prompt("add auth", summary)
        assert "added a new authentication endpoint" in result
        assert "execution context" not in result.lower()

    def test_skips_empty_lines_between_boilerplate_and_content(self) -> None:
        """Empty lines in summary are skipped during boilerplate extraction."""
        summary = (
            "[claudecodecli] isolation=workspace-write | auth=native-cli\n"
            "\n"
            "\n"
            "Added a new endpoint for user profiles."
        )
        result = _commit_message_from_prompt("add profiles", summary)
        assert "added a new endpoint" in result
        assert "claudecodecli" not in result

    def test_falls_back_to_prompt_when_summary_is_all_boilerplate(self) -> None:
        summary = (
            "Initialization phase: learn this repository.\n"
            "Execution context: this hand is running inside a non-interactive "
            "helping_hands script started by the user.\n"
            "Repository root: /tmp/repo\n"
            "Task execution phase.\n"
        )
        result = _commit_message_from_prompt("fix login crash", summary)
        # "fix" is not a conventional prefix here (no colon), so text keeps
        # "fix login crash" → _infer_commit_type detects "fix" → "fix:" prefix
        assert "login crash" in result.lower()
        assert "execution context" not in result.lower()


class TestGenerateCommitMessage:
    def _common_kwargs(self, tmp_path: Path) -> dict:
        return {
            "cmd": _SAMPLE_CMD,
            "repo_dir": tmp_path,
            "backend": "claudecodecli",
            "prompt": "add feature",
            "summary": "done",
        }

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_falls_back_to_prompt_when_cmd_is_none(
        self, _mock: MagicMock, tmp_path: Path
    ) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["cmd"] = None
        result = generate_commit_message(**kwargs)
        assert result is not None
        assert "add feature" in result  # uses prompt

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_none_when_cmd_is_none_and_no_prompt(
        self, _mock: MagicMock, tmp_path: Path
    ) -> None:
        result = generate_commit_message(
            cmd=None, repo_dir=tmp_path, backend="test", prompt="", summary=""
        )
        assert result is None

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=True,
    )
    def test_returns_none_when_disabled(self, _mock: MagicMock, tmp_path: Path) -> None:
        assert generate_commit_message(**self._common_kwargs(tmp_path)) is None

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_uncommitted_diff",
        return_value="",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_none_when_no_diff(
        self, _d: MagicMock, _g: MagicMock, tmp_path: Path
    ) -> None:
        assert generate_commit_message(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_uncommitted_diff",
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
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        assert generate_commit_message(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_uncommitted_diff",
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
            args=[], returncode=1, stdout="", stderr="error"
        )
        assert generate_commit_message(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_uncommitted_diff",
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
            args=[], returncode=0, stdout="no markers here", stderr=""
        )
        assert generate_commit_message(**self._common_kwargs(tmp_path)) is None

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_uncommitted_diff",
        return_value="diff content",
    )
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=False,
    )
    def test_returns_message_on_success(
        self,
        _d: MagicMock,
        _g: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="COMMIT_MSG: feat: add user authentication with OAuth2\n",
            stderr="",
        )
        result = generate_commit_message(**self._common_kwargs(tmp_path))
        assert result == "feat: add user authentication with OAuth2"

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._get_uncommitted_diff",
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
        assert generate_commit_message(**self._common_kwargs(tmp_path)) is None


# ---------------------------------------------------------------------------
# _commit_message_from_prompt — edge cases
# ---------------------------------------------------------------------------


class TestCommitMessageFromPromptEdgeCases:
    """Additional edge cases for _commit_message_from_prompt."""

    def test_exclamation_mark_sentence_boundary(self) -> None:
        result = _commit_message_from_prompt("", "Fixed the crash! Also updated docs.")
        assert "fixed the crash" in result
        assert "updated docs" not in result

    def test_question_mark_sentence_boundary(self) -> None:
        result = _commit_message_from_prompt("", "Did we fix the auth? Seems like it.")
        assert "did we fix the auth" in result
        assert "Seems" not in result

    def test_strips_existing_fix_prefix_and_reinfers_type(self) -> None:
        result = _commit_message_from_prompt("", "fix: resolve crash on login")
        assert result == "fix: resolve crash on login"
        assert "fix: fix:" not in result

    def test_strips_existing_refactor_prefix_and_reinfers_type(self) -> None:
        result = _commit_message_from_prompt("", "refactor: simplify auth flow")
        assert result == "refactor: simplify auth flow"

    def test_strips_existing_docs_prefix_and_reinfers_type(self) -> None:
        result = _commit_message_from_prompt("", "docs: update README")
        assert result == "docs: update README"

    def test_strips_existing_chore_prefix_and_reinfers_type(self) -> None:
        result = _commit_message_from_prompt("", "chore: bump dependencies")
        assert result == "chore: bump dependencies"

    def test_strips_existing_test_prefix_and_reinfers_type(self) -> None:
        result = _commit_message_from_prompt("", "test: add unit tests for auth")
        assert result == "test: add unit tests for auth"

    def test_strips_prefix_case_insensitive(self) -> None:
        result = _commit_message_from_prompt("", "FEAT: add dark mode")
        assert result == "feat: add dark mode"

    def test_trailing_period_removed(self) -> None:
        result = _commit_message_from_prompt("", "Added new endpoint.")
        assert not result.endswith(".")
        assert "added new endpoint" in result

    def test_single_word_summary_infers_type(self) -> None:
        result = _commit_message_from_prompt("", "Refactored")
        assert result == "refactor: refactored"

    def test_multiline_takes_first_line_only(self) -> None:
        result = _commit_message_from_prompt(
            "", "Added caching layer\n\nThis improves performance by 50%."
        )
        assert "added caching layer" in result
        assert "performance" not in result

    def test_prefix_with_colon_space_reinfers_type(self) -> None:
        result = _commit_message_from_prompt("", "ci: run linter on PRs")
        # "linter" matches "lint" keyword → "style" type
        assert result == "style: run linter on PRs"

    def test_prefix_with_parenthetical_scope_stripped(self) -> None:
        result = _commit_message_from_prompt("", "feat(auth): add JWT support")
        assert "add JWT support" in result
        assert "feat(auth)" not in result


# ---------------------------------------------------------------------------
# _parse_output — edge cases
# ---------------------------------------------------------------------------


class TestParseOutputEdgeCases:
    """Additional edge cases for _parse_output."""

    def test_pr_body_marker_inline_with_content_not_matched(self) -> None:
        """PR_BODY: with inline text is not recognized as a body marker."""
        output = "PR_TITLE: feat: test\nPR_BODY: inline content\nMore text.\n"
        assert _parse_output(output) is None

    def test_title_with_leading_whitespace_stripped(self) -> None:
        output = "PR_TITLE:    feat: spaces before title   \nPR_BODY:\nBody text.\n"
        result = _parse_output(output)
        assert result is not None
        assert result.title == "feat: spaces before title"

    def test_body_with_trailing_whitespace_stripped(self) -> None:
        output = "PR_TITLE: feat: test\nPR_BODY:\n  Body content  \n  \n"
        result = _parse_output(output)
        assert result is not None
        assert result.body == "Body content"

    def test_body_preserves_internal_blank_lines(self) -> None:
        output = "PR_TITLE: feat: test\nPR_BODY:\n## Changes\n\n- Item 1\n\n- Item 2\n"
        result = _parse_output(output)
        assert result is not None
        assert "\n\n" in result.body

    def test_title_on_later_line_still_found(self) -> None:
        output = (
            "Some preamble text\n"
            "Another line\n"
            "PR_TITLE: fix: late title\n"
            "PR_BODY:\n"
            "Body here.\n"
        )
        result = _parse_output(output)
        assert result is not None
        assert result.title == "fix: late title"


# ---------------------------------------------------------------------------
# _build_prompt — edge cases
# ---------------------------------------------------------------------------


class TestBuildPromptEdgeCases:
    """Additional edge cases for _build_prompt."""

    def test_whitespace_only_summary_omits_section(self) -> None:
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary="   \n  ",
        )
        assert "AI Summary of Changes" not in result

    def test_prompt_contains_conventional_commit_guidance(self) -> None:
        result = _build_prompt(diff="d", backend="b", user_prompt="p", summary="")
        assert "conventional commit" in result.lower()
        assert "feat:" in result

    def test_prompt_contains_72_char_title_guidance(self) -> None:
        result = _build_prompt(diff="d", backend="b", user_prompt="p", summary="")
        assert "72" in result


# ---------------------------------------------------------------------------
# _build_commit_message_prompt — edge cases
# ---------------------------------------------------------------------------


class TestBuildCommitMessagePromptEdgeCases:
    """Additional edge cases for _build_commit_message_prompt."""

    def test_whitespace_only_summary_omits_section(self) -> None:
        result = _build_commit_message_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary="   \t  ",
        )
        assert "AI Summary of Changes" not in result

    def test_prompt_enforces_single_line_instruction(self) -> None:
        result = _build_commit_message_prompt(
            diff="d", backend="b", user_prompt="p", summary=""
        )
        assert "single-line" in result.lower() or "single line" in result.lower()

    def test_prompt_enforces_72_char_limit(self) -> None:
        result = _build_commit_message_prompt(
            diff="d", backend="b", user_prompt="p", summary=""
        )
        assert "72" in result


# ---------------------------------------------------------------------------
# _is_trivial_message
# ---------------------------------------------------------------------------


class TestIsTrivialMessage:
    """Tests for _is_trivial_message that guards against meaningless messages."""

    def test_constant_value(self) -> None:
        assert _MIN_COMMIT_MSG_LENGTH == 8

    def test_good_message_is_not_trivial(self) -> None:
        assert _is_trivial_message("feat: add user authentication") is False

    def test_short_body_after_prefix_is_trivial(self) -> None:
        assert _is_trivial_message("feat: -") is True

    def test_ellipsis_only_body_is_trivial(self) -> None:
        assert _is_trivial_message("feat: ...") is True

    def test_dashes_only_body_is_trivial(self) -> None:
        assert _is_trivial_message("feat: ---") is True

    def test_punctuation_only_body_is_trivial(self) -> None:
        assert _is_trivial_message("feat: !!??") is True

    def test_single_char_body_is_trivial(self) -> None:
        assert _is_trivial_message("fix: x") is True

    def test_two_char_body_is_trivial(self) -> None:
        assert _is_trivial_message("fix: ab") is True

    def test_three_char_meaningful_body_is_not_trivial(self) -> None:
        assert _is_trivial_message("fix: abc") is False

    def test_no_prefix_short_message_is_trivial(self) -> None:
        assert _is_trivial_message("hi") is True

    def test_no_prefix_meaningful_message_is_not_trivial(self) -> None:
        assert _is_trivial_message("add user authentication") is False

    def test_whitespace_body_is_trivial(self) -> None:
        assert _is_trivial_message("feat:    ") is True

    def test_empty_body_after_prefix_is_trivial(self) -> None:
        assert _is_trivial_message("feat: ") is True

    def test_stars_and_slashes_body_is_trivial(self) -> None:
        assert _is_trivial_message("fix: **/") is True


# ---------------------------------------------------------------------------
# _parse_commit_message — trivial message rejection
# ---------------------------------------------------------------------------


class TestParseCommitMessageTrivialRejection:
    """_parse_commit_message rejects trivially short/meaningless messages."""

    def test_rejects_single_dash(self) -> None:
        assert _parse_commit_message("COMMIT_MSG: feat: -") is None

    def test_rejects_ellipsis(self) -> None:
        assert _parse_commit_message("COMMIT_MSG: feat: ...") is None

    def test_rejects_punctuation_only(self) -> None:
        assert _parse_commit_message("COMMIT_MSG: fix: !!") is None

    def test_accepts_meaningful_message(self) -> None:
        result = _parse_commit_message("COMMIT_MSG: feat: add user login")
        assert result == "feat: add user login"

    def test_accepts_short_but_meaningful(self) -> None:
        result = _parse_commit_message("COMMIT_MSG: fix: typo in readme")
        assert result == "fix: typo in readme"


# ---------------------------------------------------------------------------
# _commit_message_from_prompt — trivial text rejection
# ---------------------------------------------------------------------------


class TestCommitMessageFromPromptTrivialRejection:
    """_commit_message_from_prompt returns empty for trivially short text."""

    def test_single_char_prompt_returns_empty(self) -> None:
        assert _commit_message_from_prompt("-", "") == ""

    def test_punctuation_only_prompt_returns_empty(self) -> None:
        assert _commit_message_from_prompt("...", "") == ""

    def test_dashes_only_prompt_returns_empty(self) -> None:
        assert _commit_message_from_prompt("---", "") == ""

    def test_meaningful_prompt_returns_message(self) -> None:
        result = _commit_message_from_prompt("add login page", "")
        assert result.startswith("feat: ")
        assert len(result) > _MIN_COMMIT_MSG_LENGTH


# ---------------------------------------------------------------------------
# _truncate_text
# ---------------------------------------------------------------------------


class TestTruncateText:
    """Tests for _truncate_text helper."""

    def test_short_text_returned_as_is(self) -> None:
        assert _truncate_text("hello", limit=10) == "hello"

    def test_exact_limit_returned_as_is(self) -> None:
        assert _truncate_text("hello", limit=5) == "hello"

    def test_long_text_truncated_with_indicator(self) -> None:
        result = _truncate_text("a" * 20, limit=10)
        assert result.startswith("a" * 10)
        assert result.endswith("...[truncated]")
        assert len(result) == 10 + len("...[truncated]")

    def test_strips_whitespace_before_truncation(self) -> None:
        result = _truncate_text("  hello  ", limit=100)
        assert result == "hello"

    def test_empty_text_returns_empty(self) -> None:
        assert _truncate_text("", limit=10) == ""

    def test_whitespace_only_returns_empty(self) -> None:
        assert _truncate_text("   ", limit=10) == ""

    def test_zero_limit_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            _truncate_text("hello", limit=0)

    def test_negative_limit_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            _truncate_text("hello", limit=-1)


# ---------------------------------------------------------------------------
# _infer_commit_type
# ---------------------------------------------------------------------------


class TestInferCommitType:
    """Tests for _infer_commit_type helper."""

    def test_fix_keyword(self) -> None:
        assert _infer_commit_type("fix the login crash") == "fix"

    def test_bug_keyword(self) -> None:
        assert _infer_commit_type("resolve a bug in auth") == "fix"

    def test_crash_keyword(self) -> None:
        assert _infer_commit_type("handle crash on startup") == "fix"

    def test_refactor_keyword(self) -> None:
        assert _infer_commit_type("refactor the database layer") == "refactor"

    def test_simplify_keyword(self) -> None:
        assert _infer_commit_type("simplify the auth flow") == "refactor"

    def test_documentation_keyword(self) -> None:
        assert _infer_commit_type("update documentation for API") == "docs"

    def test_docs_keyword(self) -> None:
        assert _infer_commit_type("update the docs") == "docs"

    def test_readme_keyword(self) -> None:
        assert _infer_commit_type("update README with examples") == "docs"

    def test_test_keyword(self) -> None:
        assert _infer_commit_type("add test for new endpoint") == "test"

    def test_coverage_keyword(self) -> None:
        assert _infer_commit_type("increase coverage for auth module") == "test"

    def test_ci_keyword(self) -> None:
        assert _infer_commit_type("update ci pipeline config") == "ci"

    def test_workflow_keyword(self) -> None:
        assert _infer_commit_type("add github workflow for deploy") == "ci"

    def test_style_keyword(self) -> None:
        assert _infer_commit_type("format code with ruff") == "style"

    def test_lint_keyword(self) -> None:
        assert _infer_commit_type("run linter across codebase") == "style"

    def test_perf_keyword(self) -> None:
        assert _infer_commit_type("optimize database queries") == "perf"

    def test_performance_keyword(self) -> None:
        assert _infer_commit_type("improve performance of search") == "perf"

    def test_chore_keyword(self) -> None:
        assert _infer_commit_type("bump dependency versions") == "chore"

    def test_upgrade_keyword(self) -> None:
        assert _infer_commit_type("upgrade python to 3.13") == "chore"

    def test_default_feat(self) -> None:
        assert _infer_commit_type("add dark mode toggle") == "feat"

    def test_no_keywords_returns_feat(self) -> None:
        assert _infer_commit_type("implement new feature") == "feat"

    def test_case_insensitive(self) -> None:
        assert _infer_commit_type("FIX the login crash") == "fix"

    def test_fix_takes_priority_over_test(self) -> None:
        """'fix the test' should be 'fix' not 'test'."""
        assert _infer_commit_type("fix the test suite") == "fix"

    def test_docker_does_not_match_docs(self) -> None:
        """'docker' should not trigger 'docs' type."""
        assert _infer_commit_type("update docker config") == "feat"

    def test_dependencies_does_not_match_ci(self) -> None:
        """'dependencies' should not trigger 'ci' type."""
        assert _infer_commit_type("update dependencies") == "chore"

    def test_multi_word_keyword_clean_up(self) -> None:
        """Multi-word keyword 'clean up' triggers substring match branch."""
        assert _infer_commit_type("clean up the module") == "refactor"

    def test_multi_word_keyword_github_action(self) -> None:
        """Multi-word keyword 'github action' triggers substring match branch."""
        assert _infer_commit_type("add github action for deploy") == "ci"

    def test_keywords_dict_is_nonempty(self) -> None:
        assert len(_COMMIT_TYPE_KEYWORDS) > 0

    def test_all_types_have_keywords(self) -> None:
        for commit_type, keywords in _COMMIT_TYPE_KEYWORDS.items():
            assert len(keywords) > 0, f"{commit_type} has no keywords"


# ---------------------------------------------------------------------------
# _build_prompt — truncation indicator tests
# ---------------------------------------------------------------------------


class TestBuildPromptTruncationIndicators:
    """Tests for truncation indicators in _build_prompt."""

    def test_long_prompt_includes_truncation_indicator(self) -> None:
        long_prompt = "x" * (_PROMPT_CONTEXT_LENGTH + 100)
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt=long_prompt,
            summary="",
        )
        assert "...[truncated]" in result

    def test_short_prompt_no_truncation_indicator(self) -> None:
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt="short task",
            summary="",
        )
        assert "...[truncated]" not in result

    def test_long_summary_includes_truncation_indicator(self) -> None:
        long_summary = "s" * (_PR_SUMMARY_TRUNCATION_LENGTH + 100)
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary=long_summary,
        )
        assert "...[truncated]" in result

    def test_short_summary_no_truncation_indicator(self) -> None:
        result = _build_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary="short summary",
        )
        assert "...[truncated]" not in result


# ---------------------------------------------------------------------------
# _build_commit_message_prompt — truncation indicator tests
# ---------------------------------------------------------------------------


class TestBuildCommitMessagePromptTruncationIndicators:
    """Tests for truncation indicators in _build_commit_message_prompt."""

    def test_long_prompt_includes_truncation_indicator(self) -> None:
        long_prompt = "x" * (_PROMPT_CONTEXT_LENGTH + 100)
        result = _build_commit_message_prompt(
            diff="diff",
            backend="test",
            user_prompt=long_prompt,
            summary="",
        )
        assert "...[truncated]" in result

    def test_short_prompt_no_truncation_indicator(self) -> None:
        result = _build_commit_message_prompt(
            diff="diff",
            backend="test",
            user_prompt="short task",
            summary="",
        )
        assert "...[truncated]" not in result

    def test_long_summary_includes_truncation_indicator(self) -> None:
        long_summary = "s" * (_COMMIT_SUMMARY_TRUNCATION_LENGTH + 100)
        result = _build_commit_message_prompt(
            diff="diff",
            backend="test",
            user_prompt="task",
            summary=long_summary,
        )
        assert "...[truncated]" in result


# ---------------------------------------------------------------------------
# _commit_message_from_prompt — type inference tests
# ---------------------------------------------------------------------------


class TestCommitMessageFromPromptTypeInference:
    """_commit_message_from_prompt infers commit type from text content."""

    def test_fix_prompt_gets_fix_prefix(self) -> None:
        result = _commit_message_from_prompt("fix the login crash", "")
        assert result.startswith("fix: ")

    def test_refactor_prompt_gets_refactor_prefix(self) -> None:
        result = _commit_message_from_prompt("refactor auth module", "")
        assert result.startswith("refactor: ")

    def test_docs_prompt_gets_docs_prefix(self) -> None:
        result = _commit_message_from_prompt("update documentation for API", "")
        assert result.startswith("docs: ")

    def test_test_prompt_gets_test_prefix(self) -> None:
        result = _commit_message_from_prompt("add test for new endpoint", "")
        assert result.startswith("test: ")

    def test_generic_prompt_gets_feat_prefix(self) -> None:
        result = _commit_message_from_prompt("add dark mode toggle", "")
        assert result.startswith("feat: ")

    def test_chore_prompt_gets_chore_prefix(self) -> None:
        result = _commit_message_from_prompt("bump dependency versions", "")
        assert result.startswith("chore: ")

    def test_perf_prompt_gets_perf_prefix(self) -> None:
        result = _commit_message_from_prompt("optimize database queries", "")
        assert result.startswith("perf: ")


# ---------------------------------------------------------------------------
# _COMMIT_MSG_DIFF_LIMIT and _COMMIT_MSG_TIMEOUT constants (v147)
# ---------------------------------------------------------------------------


class TestCommitMsgConstants:
    """Tests for commit message generation constant values and types."""

    def test_commit_msg_diff_limit_is_positive_int(self) -> None:
        assert isinstance(_COMMIT_MSG_DIFF_LIMIT, int)
        assert _COMMIT_MSG_DIFF_LIMIT > 0

    def test_commit_msg_diff_limit_value(self) -> None:
        assert _COMMIT_MSG_DIFF_LIMIT == 8_000

    def test_commit_msg_timeout_is_positive_float(self) -> None:
        assert isinstance(_COMMIT_MSG_TIMEOUT, float)
        assert _COMMIT_MSG_TIMEOUT > 0

    def test_commit_msg_timeout_value(self) -> None:
        assert _COMMIT_MSG_TIMEOUT == 30.0

    def test_commit_msg_diff_limit_has_docstring(self) -> None:
        """Verify the constant has a module-level docstring annotation."""
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        src = inspect.getsource(mod)
        assert '_COMMIT_MSG_DIFF_LIMIT = 8_000\n"""' in src

    def test_commit_msg_timeout_has_docstring(self) -> None:
        """Verify the constant has a module-level docstring annotation."""
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        src = inspect.getsource(mod)
        assert '_COMMIT_MSG_TIMEOUT = 30.0\n"""' in src


# ---------------------------------------------------------------------------
# cli_label dead code removal (v147)
# ---------------------------------------------------------------------------


class TestCliLabelSimplification:
    """Verify cli_label uses cmd[0] directly (dead fallback removed)."""

    def test_generate_pr_description_uses_cmd_zero(self, tmp_path: Path) -> None:
        """generate_pr_description uses cmd[0] as cli_label."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        mock_result.stdout = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
                return_value=False,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description._get_diff",
                return_value="diff content",
            ),
        ):
            result = generate_pr_description(
                cmd=["my-cli", "-p"],
                repo_dir=tmp_path,
                base_branch="main",
                backend="test",
                prompt="task",
                summary="summary",
            )
            assert result is None  # fails due to returncode=1

    def test_generate_commit_message_uses_cmd_zero(self, tmp_path: Path) -> None:
        """generate_commit_message uses cmd[0] as cli_label."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        mock_result.stdout = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
                return_value=False,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description._get_uncommitted_diff",
                return_value="diff content",
            ),
        ):
            result = generate_commit_message(
                cmd=["my-cli", "-p"],
                repo_dir=tmp_path,
                backend="test",
                prompt="task",
                summary="summary",
            )
            assert result is None  # fails due to returncode=1


# ---------------------------------------------------------------------------
# Parser marker constants (v174)
# ---------------------------------------------------------------------------


class TestParserMarkerConstants:
    """Tests for PR/commit message parser marker constants."""

    def test_pr_title_marker_value(self) -> None:
        assert _PR_TITLE_MARKER == "PR_TITLE:"

    def test_pr_title_marker_is_str(self) -> None:
        assert isinstance(_PR_TITLE_MARKER, str)

    def test_pr_body_marker_value(self) -> None:
        assert _PR_BODY_MARKER == "PR_BODY:"

    def test_pr_body_marker_is_str(self) -> None:
        assert isinstance(_PR_BODY_MARKER, str)

    def test_commit_msg_marker_value(self) -> None:
        assert _COMMIT_MSG_MARKER == "COMMIT_MSG:"

    def test_commit_msg_marker_is_str(self) -> None:
        assert isinstance(_COMMIT_MSG_MARKER, str)

    def test_pr_title_marker_ends_with_colon(self) -> None:
        assert _PR_TITLE_MARKER.endswith(":")

    def test_pr_body_marker_ends_with_colon(self) -> None:
        assert _PR_BODY_MARKER.endswith(":")

    def test_commit_msg_marker_ends_with_colon(self) -> None:
        assert _COMMIT_MSG_MARKER.endswith(":")

    def test_build_prompt_uses_pr_title_marker(self) -> None:
        """_build_prompt output contains the _PR_TITLE_MARKER constant."""
        prompt = _build_prompt(diff="x", backend="b", user_prompt="p", summary="")
        assert _PR_TITLE_MARKER in prompt

    def test_build_prompt_uses_pr_body_marker(self) -> None:
        """_build_prompt output contains the _PR_BODY_MARKER constant."""
        prompt = _build_prompt(diff="x", backend="b", user_prompt="p", summary="")
        assert _PR_BODY_MARKER in prompt

    def test_build_commit_message_prompt_uses_commit_msg_marker(self) -> None:
        """_build_commit_message_prompt output contains _COMMIT_MSG_MARKER."""
        prompt = _build_commit_message_prompt(
            diff="x", backend="b", user_prompt="p", summary=""
        )
        assert _COMMIT_MSG_MARKER in prompt

    def test_parse_output_uses_pr_title_marker(self) -> None:
        """_parse_output correctly parses output using the marker constants."""
        output = f"{_PR_TITLE_MARKER} My Title\n{_PR_BODY_MARKER}\nBody text"
        result = _parse_output(output)
        assert result is not None
        assert result.title == "My Title"
        assert result.body == "Body text"

    def test_parse_commit_message_uses_commit_msg_marker(self) -> None:
        """_parse_commit_message correctly parses using the marker constant."""
        output = f"{_COMMIT_MSG_MARKER} feat: add new feature"
        result = _parse_commit_message(output)
        assert result == "feat: add new feature"


# ---------------------------------------------------------------------------
# _COMMIT_TYPE_PREFIX_RE constant (v174)
# ---------------------------------------------------------------------------


class TestCommitTypePrefixRe:
    """Tests for the DRYed commit type prefix regex constant."""

    def test_is_compiled_pattern(self) -> None:
        import re

        assert isinstance(_COMMIT_TYPE_PREFIX_RE, re.Pattern)

    def test_case_insensitive_flag(self) -> None:
        import re

        assert _COMMIT_TYPE_PREFIX_RE.flags & re.IGNORECASE

    def test_matches_feat_prefix(self) -> None:
        assert _COMMIT_TYPE_PREFIX_RE.match("feat: add feature")

    def test_matches_fix_prefix(self) -> None:
        assert _COMMIT_TYPE_PREFIX_RE.match("fix: repair bug")

    def test_matches_prefix_with_scope(self) -> None:
        assert _COMMIT_TYPE_PREFIX_RE.match("feat(auth): add login")

    def test_no_match_plain_text(self) -> None:
        assert _COMMIT_TYPE_PREFIX_RE.match("plain text") is None

    def test_is_trivial_uses_constant(self) -> None:
        """_is_trivial_message uses _COMMIT_TYPE_PREFIX_RE to strip prefix."""
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        src = inspect.getsource(mod._is_trivial_message)
        assert "_COMMIT_TYPE_PREFIX_RE" in src

    def test_commit_message_from_prompt_uses_constant(self) -> None:
        """_commit_message_from_prompt uses _COMMIT_TYPE_PREFIX_RE."""
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        src = inspect.getsource(mod._commit_message_from_prompt)
        assert "_COMMIT_TYPE_PREFIX_RE" in src

    def test_marker_constants_have_docstrings(self) -> None:
        """All new constants have module-level docstring annotations."""
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        src = inspect.getsource(mod)
        assert '_PR_TITLE_MARKER = "PR_TITLE:"\n"""' in src
        assert '_PR_BODY_MARKER = "PR_BODY:"\n"""' in src
        assert '_COMMIT_MSG_MARKER = "COMMIT_MSG:"\n"""' in src


# ---------------------------------------------------------------------------
# v189 — generate_pr_description input validation
# ---------------------------------------------------------------------------


class TestGeneratePRDescriptionInputValidation:
    """Verify generate_pr_description rejects empty/whitespace params."""

    def _common_kwargs(self, tmp_path: Path) -> dict:
        return {
            "cmd": ["claude", "-p"],
            "repo_dir": tmp_path,
            "base_branch": "main",
            "backend": "claudecodecli",
            "prompt": "add feature",
            "summary": "done",
        }

    def test_empty_base_branch_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["base_branch"] = ""
        with pytest.raises(ValueError, match="base_branch"):
            generate_pr_description(**kwargs)

    def test_whitespace_base_branch_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["base_branch"] = "   "
        with pytest.raises(ValueError, match="base_branch"):
            generate_pr_description(**kwargs)

    def test_tab_base_branch_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["base_branch"] = "\t"
        with pytest.raises(ValueError, match="base_branch"):
            generate_pr_description(**kwargs)

    def test_empty_backend_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["backend"] = ""
        with pytest.raises(ValueError, match="backend"):
            generate_pr_description(**kwargs)

    def test_whitespace_backend_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["backend"] = "  \n  "
        with pytest.raises(ValueError, match="backend"):
            generate_pr_description(**kwargs)

    def test_cmd_none_skips_validation(self, tmp_path: Path) -> None:
        """When cmd is None, validation is skipped (early return)."""
        kwargs = self._common_kwargs(tmp_path)
        kwargs["cmd"] = None
        kwargs["base_branch"] = ""
        kwargs["backend"] = ""
        assert generate_pr_description(**kwargs) is None

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=True,
    )
    def test_valid_params_reach_disabled_check(
        self, _mock: MagicMock, tmp_path: Path
    ) -> None:
        """Valid base_branch and backend pass validation."""
        result = generate_pr_description(**self._common_kwargs(tmp_path))
        assert result is None  # disabled, but no ValueError


# ---------------------------------------------------------------------------
# v189 — generate_commit_message backend validation
# ---------------------------------------------------------------------------


class TestGenerateCommitMessageBackendValidation:
    """Verify generate_commit_message rejects empty/whitespace backend."""

    def _common_kwargs(self, tmp_path: Path) -> dict:
        return {
            "cmd": ["claude", "-p"],
            "repo_dir": tmp_path,
            "backend": "claudecodecli",
            "prompt": "fix bug",
            "summary": "fixed",
        }

    def test_empty_backend_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["backend"] = ""
        with pytest.raises(ValueError, match="backend"):
            generate_commit_message(**kwargs)

    def test_whitespace_backend_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["backend"] = "   "
        with pytest.raises(ValueError, match="backend"):
            generate_commit_message(**kwargs)

    def test_tab_backend_raises(self, tmp_path: Path) -> None:
        kwargs = self._common_kwargs(tmp_path)
        kwargs["backend"] = "\t\n"
        with pytest.raises(ValueError, match="backend"):
            generate_commit_message(**kwargs)

    @patch(
        "helping_hands.lib.hands.v1.hand.pr_description._is_disabled",
        return_value=True,
    )
    def test_valid_backend_passes_validation(
        self, _mock: MagicMock, tmp_path: Path
    ) -> None:
        """Valid backend passes validation (returns None because disabled)."""
        result = generate_commit_message(**self._common_kwargs(tmp_path))
        assert result is None


# ---------------------------------------------------------------------------
# Pre-compiled boilerplate regex constants (v190)
# ---------------------------------------------------------------------------


class TestBracketBannerRe:
    """Tests for the pre-compiled _BRACKET_BANNER_RE constant."""

    def test_is_compiled_pattern(self) -> None:
        import re

        assert isinstance(_BRACKET_BANNER_RE, re.Pattern)

    def test_matches_label_banner(self) -> None:
        assert _BRACKET_BANNER_RE.match("[INFO] key=value")

    def test_matches_nested_brackets(self) -> None:
        assert _BRACKET_BANNER_RE.match("[some.label] data here")

    def test_no_match_plain_text(self) -> None:
        assert _BRACKET_BANNER_RE.match("plain text") is None

    def test_no_match_bracket_no_space(self) -> None:
        assert _BRACKET_BANNER_RE.match("[label]nospace") is None

    def test_boilerplate_uses_constant(self) -> None:
        """_is_boilerplate_line uses _BRACKET_BANNER_RE."""
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        src = inspect.getsource(mod._is_boilerplate_line)
        assert "_BRACKET_BANNER_RE" in src


class TestNumberedListRe:
    """Tests for the pre-compiled _NUMBERED_LIST_RE constant."""

    def test_is_compiled_pattern(self) -> None:
        import re

        assert isinstance(_NUMBERED_LIST_RE, re.Pattern)

    def test_matches_numbered_item(self) -> None:
        assert _NUMBERED_LIST_RE.match("1. Read README.md")

    def test_matches_two_digit(self) -> None:
        assert _NUMBERED_LIST_RE.match("12. Step twelve")

    def test_no_match_plain_text(self) -> None:
        assert _NUMBERED_LIST_RE.match("plain text") is None

    def test_no_match_no_space(self) -> None:
        assert _NUMBERED_LIST_RE.match("1.nospace") is None

    def test_boilerplate_uses_constant(self) -> None:
        """_is_boilerplate_line uses _NUMBERED_LIST_RE."""
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        src = inspect.getsource(mod._is_boilerplate_line)
        assert "_NUMBERED_LIST_RE" in src


class TestModuleLevelReImport:
    """Verify re is imported at module level (v190 DRY improvement)."""

    def test_re_in_module_globals(self) -> None:
        import helping_hands.lib.hands.v1.hand.pr_description as mod

        assert hasattr(mod, "re")

    def test_no_function_local_re_imports(self) -> None:
        """No function should have a local ``import re`` statement."""
        import ast
        import inspect

        import helping_hands.lib.hands.v1.hand.pr_description as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        local_re_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Import):
                        for alias in child.names:
                            if alias.name == "re":
                                local_re_imports.append(node.name)
        assert local_re_imports == [], (
            f"Functions with local 'import re': {local_re_imports}"
        )
