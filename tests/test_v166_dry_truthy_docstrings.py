"""Tests for v166: consolidated _FAILURE_OUTPUT_TAIL_LENGTH, _CLI_TRUTHY_VALUES, docstrings."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. _FAILURE_OUTPUT_TAIL_LENGTH consolidation
# ---------------------------------------------------------------------------


class TestFailureOutputTailConsolidation:
    """Verify _FAILURE_OUTPUT_TAIL_LENGTH is exported from cli/base.py and
    re-exported identically by all 4 CLI hand subclass modules."""

    def test_base_defines_constant(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FAILURE_OUTPUT_TAIL_LENGTH,
        )

        assert _FAILURE_OUTPUT_TAIL_LENGTH == 2000

    def test_base_constant_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FAILURE_OUTPUT_TAIL_LENGTH,
        )

        assert _FAILURE_OUTPUT_TAIL_LENGTH > 0

    def test_subclasses_use_detect_auth_failure(self) -> None:
        """Since v203, subclasses use _detect_auth_failure which
        encapsulates _FAILURE_OUTPUT_TAIL_LENGTH internally."""
        import inspect

        from helping_hands.lib.hands.v1.hand.cli import claude, codex, gemini, opencode

        for mod in (claude, codex, gemini, opencode):
            src = inspect.getsource(mod)
            assert "_detect_auth_failure" in src, (
                f"{mod.__name__} should use _detect_auth_failure"
            )

    def test_constant_in_base_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import __all__

        assert "_FAILURE_OUTPUT_TAIL_LENGTH" in __all__


# ---------------------------------------------------------------------------
# 2. _CLI_TRUTHY_VALUES harmonization
# ---------------------------------------------------------------------------


class TestCLITruthyValues:
    """Verify _CLI_TRUTHY_VALUES extends config _TRUTHY_VALUES with 'on'."""

    def test_cli_truthy_is_frozenset(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CLI_TRUTHY_VALUES

        assert isinstance(_CLI_TRUTHY_VALUES, frozenset)

    def test_cli_truthy_contains_config_values(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES
        from helping_hands.lib.hands.v1.hand.cli.base import _CLI_TRUTHY_VALUES

        assert _TRUTHY_VALUES.issubset(_CLI_TRUTHY_VALUES)

    def test_cli_truthy_contains_on(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CLI_TRUTHY_VALUES

        assert "on" in _CLI_TRUTHY_VALUES

    def test_cli_truthy_expected_members(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CLI_TRUTHY_VALUES

        assert frozenset({"1", "true", "yes", "on"}) == _CLI_TRUTHY_VALUES

    def test_is_truthy_uses_cli_truthy_values(self) -> None:
        """_is_truthy should accept 'on' (via _CLI_TRUTHY_VALUES)."""
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("on") is True

    def test_is_truthy_accepts_standard_truthy(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("1") is True
        assert _TwoPhaseCLIHand._is_truthy("true") is True
        assert _TwoPhaseCLIHand._is_truthy("yes") is True

    def test_is_truthy_rejects_falsy(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("0") is False
        assert _TwoPhaseCLIHand._is_truthy("false") is False
        assert _TwoPhaseCLIHand._is_truthy("no") is False
        assert _TwoPhaseCLIHand._is_truthy("") is False

    def test_is_truthy_none_returns_false(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy(None) is False

    def test_is_truthy_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy.__doc__
        assert "truthy" in _TwoPhaseCLIHand._is_truthy.__doc__.lower()


# ---------------------------------------------------------------------------
# 3. Codex CLI hand docstrings
# ---------------------------------------------------------------------------


class TestCodexDocstrings:
    """Verify Google-style docstrings on CodexCLIHand methods."""

    def test_native_cli_auth_env_names_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._native_cli_auth_env_names.__doc__
        assert doc
        assert "OPENAI_API_KEY" in doc

    def test_build_codex_failure_message_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._build_codex_failure_message.__doc__
        assert doc
        assert "Args:" in doc
        assert "Returns:" in doc

    def test_normalize_base_command_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._normalize_base_command.__doc__
        assert doc
        assert "codex" in doc.lower()

    def test_apply_codex_exec_sandbox_defaults_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._apply_codex_exec_sandbox_defaults.__doc__
        assert doc
        assert "sandbox" in doc.lower()

    def test_auto_sandbox_mode_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._auto_sandbox_mode.__doc__
        assert doc
        assert "Docker" in doc

    def test_skip_git_repo_check_enabled_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._skip_git_repo_check_enabled.__doc__
        assert doc
        assert "HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK" in doc

    def test_apply_codex_exec_git_repo_check_defaults_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._apply_codex_exec_git_repo_check_defaults.__doc__
        assert doc
        assert "skip-git-repo-check" in doc

    def test_apply_backend_defaults_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._apply_backend_defaults.__doc__
        assert doc
        assert "sandbox" in doc.lower()

    def test_build_failure_message_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._build_failure_message.__doc__
        assert doc
        assert "Returns:" in doc

    def test_command_not_found_message_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._command_not_found_message.__doc__
        assert doc
        assert "Args:" in doc

    def test_invoke_codex_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._invoke_codex.__doc__
        assert doc
        assert "prompt" in doc.lower()

    def test_invoke_backend_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        doc = CodexCLIHand._invoke_backend.__doc__
        assert doc
        assert "_invoke_codex" in doc


# ---------------------------------------------------------------------------
# 4. Gemini CLI hand docstrings
# ---------------------------------------------------------------------------


class TestGeminiDocstrings:
    """Verify Google-style docstrings on GeminiCLIHand methods."""

    def test_pr_description_cmd_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._pr_description_cmd.__doc__
        assert doc
        assert "Returns:" in doc

    def test_describe_auth_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._describe_auth.__doc__
        assert doc
        assert "GEMINI_API_KEY" in doc

    def test_looks_like_model_not_found_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._looks_like_model_not_found.__doc__
        assert doc
        assert "model" in doc.lower()

    def test_extract_unavailable_model_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._extract_unavailable_model.__doc__
        assert doc
        assert "Args:" in doc

    def test_strip_model_args_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._strip_model_args.__doc__
        assert doc
        assert "--model" in doc

    def test_has_approval_mode_flag_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._has_approval_mode_flag.__doc__
        assert doc
        assert "approval-mode" in doc

    def test_apply_backend_defaults_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._apply_backend_defaults.__doc__
        assert doc
        assert "approval-mode" in doc.lower()

    def test_build_gemini_failure_message_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._build_gemini_failure_message.__doc__
        assert doc
        assert "Args:" in doc
        assert "Returns:" in doc

    def test_build_subprocess_env_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._build_subprocess_env.__doc__
        assert doc
        assert "GEMINI_API_KEY" in doc

    def test_build_failure_message_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._build_failure_message.__doc__
        assert doc
        assert "Returns:" in doc

    def test_command_not_found_message_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._command_not_found_message.__doc__
        assert doc
        assert "Args:" in doc

    def test_retry_command_after_failure_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._retry_command_after_failure.__doc__
        assert doc
        assert "model" in doc.lower()

    def test_invoke_gemini_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._invoke_gemini.__doc__
        assert doc
        assert "prompt" in doc.lower()

    def test_invoke_backend_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        doc = GeminiCLIHand._invoke_backend.__doc__
        assert doc
        assert "_invoke_gemini" in doc
