"""Tests for GeminiCLIHand static/pure helper methods."""

from __future__ import annotations

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_gemini_hand(tmp_path, model="gemini-2.0-flash"):
    (tmp_path / "main.py").write_text("")
    config = Config(repo=str(tmp_path), model=model)
    repo_index = RepoIndex.from_path(tmp_path)
    return GeminiCLIHand(config=config, repo_index=repo_index)


@pytest.fixture()
def gemini_hand(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return _make_gemini_hand(tmp_path)


# ---------------------------------------------------------------------------
# _looks_like_model_not_found
# ---------------------------------------------------------------------------


class TestLooksLikeModelNotFound:
    def test_detects_model_not_found_error(self) -> None:
        assert GeminiCLIHand._looks_like_model_not_found("ModelNotFoundError: xyz")

    def test_detects_no_longer_available(self) -> None:
        assert GeminiCLIHand._looks_like_model_not_found(
            "models/gemini-1.0 is no longer available to new users"
        )

    def test_detects_model_not_found_combination(self) -> None:
        assert GeminiCLIHand._looks_like_model_not_found(
            "Error: models/gemini-exp not found"
        )

    def test_false_for_generic_error(self) -> None:
        assert not GeminiCLIHand._looks_like_model_not_found("network timeout")

    def test_case_insensitive(self) -> None:
        assert GeminiCLIHand._looks_like_model_not_found("MODELNOTFOUNDERROR: abc")


# ---------------------------------------------------------------------------
# _extract_unavailable_model
# ---------------------------------------------------------------------------


class TestExtractUnavailableModel:
    def test_extracts_model_name(self) -> None:
        assert (
            GeminiCLIHand._extract_unavailable_model("Error: models/gemini-1.0-pro")
            == "gemini-1.0-pro"
        )

    def test_returns_empty_when_no_match(self) -> None:
        assert GeminiCLIHand._extract_unavailable_model("generic error") == ""

    def test_extracts_model_with_dots_and_hyphens(self) -> None:
        result = GeminiCLIHand._extract_unavailable_model(
            "models/gemini-2.5-pro-preview-06-05"
        )
        assert result == "gemini-2.5-pro-preview-06-05"


# ---------------------------------------------------------------------------
# _strip_model_args
# ---------------------------------------------------------------------------


class TestStripModelArgs:
    def test_strips_model_flag_with_value(self) -> None:
        cmd = ["gemini", "--model", "gemini-1.0", "-p", "hello"]
        result = GeminiCLIHand._strip_model_args(cmd)
        assert result == ["gemini", "-p", "hello"]

    def test_strips_model_equals_syntax(self) -> None:
        cmd = ["gemini", "--model=gemini-1.0", "-p", "hello"]
        result = GeminiCLIHand._strip_model_args(cmd)
        assert result == ["gemini", "-p", "hello"]

    def test_returns_none_when_no_model(self) -> None:
        cmd = ["gemini", "-p", "hello"]
        assert GeminiCLIHand._strip_model_args(cmd) is None

    def test_model_at_end_of_cmd(self) -> None:
        cmd = ["gemini", "-p", "hello", "--model", "gemini-2.0"]
        result = GeminiCLIHand._strip_model_args(cmd)
        assert result == ["gemini", "-p", "hello"]

    def test_model_flag_at_end_without_value(self) -> None:
        cmd = ["gemini", "-p", "hello", "--model"]
        result = GeminiCLIHand._strip_model_args(cmd)
        assert result == ["gemini", "-p", "hello"]


# ---------------------------------------------------------------------------
# _has_approval_mode_flag
# ---------------------------------------------------------------------------


class TestHasApprovalModeFlag:
    def test_detects_flag(self) -> None:
        assert GeminiCLIHand._has_approval_mode_flag(
            ["gemini", "--approval-mode", "auto_edit"]
        )

    def test_detects_equals_syntax(self) -> None:
        assert GeminiCLIHand._has_approval_mode_flag(
            ["gemini", "--approval-mode=auto_edit"]
        )

    def test_false_when_absent(self) -> None:
        assert not GeminiCLIHand._has_approval_mode_flag(["gemini", "-p", "hello"])


# ---------------------------------------------------------------------------
# _apply_backend_defaults
# ---------------------------------------------------------------------------


class TestApplyBackendDefaults:
    def test_adds_approval_mode(self, gemini_hand) -> None:
        cmd = ["gemini", "-p", "hello"]
        result = gemini_hand._apply_backend_defaults(cmd)
        assert "--approval-mode" in result
        assert "auto_edit" in result

    def test_no_inject_when_present(self, gemini_hand) -> None:
        cmd = ["gemini", "--approval-mode", "manual", "-p", "hello"]
        result = gemini_hand._apply_backend_defaults(cmd)
        assert result.count("--approval-mode") == 1
        assert "manual" in result

    def test_non_gemini_passthrough(self, gemini_hand) -> None:
        cmd = ["other-tool", "-p", "hello"]
        result = gemini_hand._apply_backend_defaults(cmd)
        assert result == cmd


# ---------------------------------------------------------------------------
# _build_gemini_failure_message
# ---------------------------------------------------------------------------


class TestBuildGeminiFailureMessage:
    def test_generic_failure(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="something failed"
        )
        assert "Gemini CLI failed (exit=1)" in msg

    def test_auth_failure(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg
        assert "GEMINI_API_KEY" in msg

    def test_auth_failure_invalid_key(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="invalid api key"
        )
        assert "authentication failed" in msg

    def test_model_not_found(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="ModelNotFoundError: models/gemini-1.0-pro"
        )
        assert "unavailable" in msg
        assert "gemini-1.0-pro" in msg

    def test_model_not_found_no_longer_available(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1,
            output="models/gemini-exp is no longer available to new users",
        )
        assert "unavailable" in msg


# ---------------------------------------------------------------------------
# _retry_command_after_failure
# ---------------------------------------------------------------------------


class TestRetryCommandAfterFailure:
    def test_retries_on_model_not_found(self, gemini_hand) -> None:
        cmd = ["gemini", "--model", "gemini-1.0", "-p", "hello"]
        output = "ModelNotFoundError: models/gemini-1.0"
        result = gemini_hand._retry_command_after_failure(
            cmd, output=output, return_code=1
        )
        assert result is not None
        assert "--model" not in result

    def test_no_retry_on_success(self, gemini_hand) -> None:
        cmd = ["gemini", "--model", "gemini-1.0", "-p", "hello"]
        result = gemini_hand._retry_command_after_failure(
            cmd, output="ok", return_code=0
        )
        assert result is None

    def test_no_retry_on_other_error(self, gemini_hand) -> None:
        cmd = ["gemini", "--model", "gemini-1.0", "-p", "hello"]
        result = gemini_hand._retry_command_after_failure(
            cmd, output="network error", return_code=1
        )
        assert result is None

    def test_no_retry_when_no_model_to_strip(self, gemini_hand) -> None:
        cmd = ["gemini", "-p", "hello"]
        output = "ModelNotFoundError: models/default"
        result = gemini_hand._retry_command_after_failure(
            cmd, output=output, return_code=1
        )
        # _strip_model_args returns None when no --model flag found
        assert result is None


# ---------------------------------------------------------------------------
# _build_subprocess_env
# ---------------------------------------------------------------------------


class TestBuildSubprocessEnv:
    def test_raises_when_no_api_key(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        hand = _make_gemini_hand(tmp_path, model="gemini-2.0")
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            hand._build_subprocess_env()

    def test_raises_when_empty_api_key(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "  ")
        hand = _make_gemini_hand(tmp_path, model="gemini-2.0")
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            hand._build_subprocess_env()

    def test_succeeds_with_api_key(self, gemini_hand) -> None:
        env = gemini_hand._build_subprocess_env()
        assert "GEMINI_API_KEY" in env
