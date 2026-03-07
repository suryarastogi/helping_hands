"""Tests for helping_hands.lib.hands.v1.hand.pr_description."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.pr_description import (
    PRDescription,
    _build_commit_message_prompt,
    _build_prompt,
    _commit_message_from_prompt,
    _diff_char_limit,
    _get_diff,
    _get_uncommitted_diff,
    _is_disabled,
    _parse_commit_message,
    _parse_output,
    _timeout_seconds,
    _truncate_diff,
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

    def test_ignores_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT", "-100")
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

    def test_falls_back_to_prompt_when_summary_is_all_boilerplate(self) -> None:
        summary = (
            "Initialization phase: learn this repository.\n"
            "Execution context: this hand is running inside a non-interactive "
            "helping_hands script started by the user.\n"
            "Repository root: /tmp/repo\n"
            "Task execution phase.\n"
        )
        result = _commit_message_from_prompt("fix login crash", summary)
        # "fix" prefix is stripped and re-added as "feat:"
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

    def test_strips_existing_fix_prefix(self) -> None:
        result = _commit_message_from_prompt("", "fix: resolve crash on login")
        assert result == "feat: resolve crash on login"
        assert "fix: fix:" not in result

    def test_strips_existing_refactor_prefix(self) -> None:
        result = _commit_message_from_prompt("", "refactor: simplify auth flow")
        assert result == "feat: simplify auth flow"

    def test_strips_existing_docs_prefix(self) -> None:
        result = _commit_message_from_prompt("", "docs: update README")
        assert result == "feat: update README"

    def test_strips_existing_chore_prefix(self) -> None:
        result = _commit_message_from_prompt("", "chore: bump dependencies")
        assert result == "feat: bump dependencies"

    def test_strips_existing_test_prefix(self) -> None:
        result = _commit_message_from_prompt("", "test: add unit tests for auth")
        assert result == "feat: add unit tests for auth"

    def test_strips_prefix_case_insensitive(self) -> None:
        result = _commit_message_from_prompt("", "FEAT: add dark mode")
        assert result == "feat: add dark mode"

    def test_trailing_period_removed(self) -> None:
        result = _commit_message_from_prompt("", "Added new endpoint.")
        assert not result.endswith(".")
        assert "added new endpoint" in result

    def test_single_word_summary(self) -> None:
        result = _commit_message_from_prompt("", "Refactored")
        assert result == "feat: refactored"

    def test_multiline_takes_first_line_only(self) -> None:
        result = _commit_message_from_prompt(
            "", "Added caching layer\n\nThis improves performance by 50%."
        )
        assert "added caching layer" in result
        assert "performance" not in result

    def test_prefix_with_colon_space(self) -> None:
        result = _commit_message_from_prompt("", "ci: run linter on PRs")
        assert result == "feat: run linter on PRs"

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
