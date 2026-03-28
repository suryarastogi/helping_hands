"""Tests for GeminiCLIHand static/pure helper methods.

GeminiCLIHand wraps the `gemini` CLI and adds: --approval-mode auto_edit
injection (prevents interactive approval prompts), model-not-found retry logic
(strips the --model flag and retries without it when a model is unavailable),
and GEMINI_API_KEY presence enforcement. The approval-mode tests protect a
critical non-interactive invariant — without it Gemini blocks waiting for user
input. The model-not-found retry tests protect against deprecated Gemini model
names causing hard failures instead of graceful fallback. GEMINI_API_KEY
validation at subprocess-env build time gives an early, actionable error rather
than a cryptic subprocess failure.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def gemini_hand(make_cli_hand, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return make_cli_hand(GeminiCLIHand, model="gemini-2.0-flash")


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
    def test_raises_when_no_api_key(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        hand = make_cli_hand(GeminiCLIHand, model="gemini-2.0")
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            hand._build_subprocess_env()

    def test_raises_when_empty_api_key(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "  ")
        hand = make_cli_hand(GeminiCLIHand, model="gemini-2.0")
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            hand._build_subprocess_env()

    def test_succeeds_with_api_key(self, gemini_hand) -> None:
        env = gemini_hand._build_subprocess_env()
        assert "GEMINI_API_KEY" in env


# ---------------------------------------------------------------------------
# _describe_auth
# ---------------------------------------------------------------------------


class TestDescribeAuth:
    def test_key_set(self, gemini_hand) -> None:
        result = gemini_hand._describe_auth()
        assert "GEMINI_API_KEY" in result
        assert "(set)" in result

    def test_key_not_set(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        hand = make_cli_hand(GeminiCLIHand)
        result = hand._describe_auth()
        assert "GEMINI_API_KEY" in result
        assert "(not set)" in result

    def test_key_empty(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "  ")
        hand = make_cli_hand(GeminiCLIHand)
        result = hand._describe_auth()
        assert "(not set)" in result


# ---------------------------------------------------------------------------
# _pr_description_cmd
# ---------------------------------------------------------------------------


class TestPrDescriptionCmd:
    @patch("shutil.which", return_value="/usr/bin/gemini")
    def test_returns_cmd_when_found(self, _mock_which, gemini_hand) -> None:
        result = gemini_hand._pr_description_cmd()
        assert result == ["gemini", "-p"]

    @patch("shutil.which", return_value=None)
    def test_returns_none_when_not_found(self, _mock_which, gemini_hand) -> None:
        assert gemini_hand._pr_description_cmd() is None


# ---------------------------------------------------------------------------
# _build_failure_message (instance delegation)
# ---------------------------------------------------------------------------


class TestBuildFailureMessageInstance:
    def test_delegates_to_static_method(self, gemini_hand) -> None:
        msg = gemini_hand._build_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg
        assert "GEMINI_API_KEY" in msg

    def test_generic_error_delegation(self, gemini_hand) -> None:
        msg = gemini_hand._build_failure_message(
            return_code=42, output="something broke"
        )
        assert "Gemini CLI failed (exit=42)" in msg


# ---------------------------------------------------------------------------
# _invoke_gemini / _invoke_backend async tests
# ---------------------------------------------------------------------------


class TestInvokeGemini:
    def test_invoke_gemini_delegates_to_invoke_cli(
        self, gemini_hand, monkeypatch
    ) -> None:
        import asyncio

        calls: list[str] = []

        async def fake_invoke_cli(prompt, *, emit):
            calls.append(prompt)
            return "result"

        monkeypatch.setattr(gemini_hand, "_invoke_cli", fake_invoke_cli)

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(gemini_hand._invoke_gemini("fix it", emit=emit))
        assert result == "result"
        assert calls == ["fix it"]

    def test_invoke_backend_delegates_to_invoke_gemini(
        self, gemini_hand, monkeypatch
    ) -> None:
        import asyncio

        calls: list[str] = []

        async def fake_invoke_gemini(prompt, *, emit):
            calls.append(prompt)
            return "delegated"

        monkeypatch.setattr(gemini_hand, "_invoke_gemini", fake_invoke_gemini)

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(gemini_hand._invoke_backend("hello", emit=emit))
        assert result == "delegated"
        assert calls == ["hello"]


# ---------------------------------------------------------------------------
# _command_not_found_message
# ---------------------------------------------------------------------------


class TestCommandNotFoundMessage:
    def test_includes_command_and_env_var(self, gemini_hand) -> None:
        msg = gemini_hand._command_not_found_message("gemini")
        assert "'gemini'" in msg
        assert "HELPING_HANDS_GEMINI_CLI_CMD" in msg
