"""Tests for v167: goose/opencode/e2e docstrings and constant extraction."""

from __future__ import annotations

import inspect

# ---------------------------------------------------------------------------
# 1. Goose CLI hand docstrings (13 methods)
# ---------------------------------------------------------------------------

_GOOSE_METHODS = (
    "_pr_description_cmd",
    "_describe_auth",
    "_normalize_base_command",
    "_resolve_cli_model",
    "_has_goose_builtin_flag",
    "_apply_backend_defaults",
    "_command_not_found_message",
    "_normalize_goose_provider",
    "_infer_goose_provider_from_model",
    "_normalize_ollama_host",
    "_resolve_ollama_host",
    "_resolve_goose_provider_model_from_config",
    "_build_subprocess_env",
)


class TestGooseDocstrings:
    """Verify all GooseCLIHand methods have Google-style docstrings."""

    def _get_cls(self):
        from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

        return GooseCLIHand

    def test_all_target_methods_have_docstrings(self) -> None:
        cls = self._get_cls()
        for name in _GOOSE_METHODS:
            method = getattr(cls, name)
            doc = inspect.getdoc(method)
            assert doc, f"GooseCLIHand.{name} missing docstring"

    def test_docstrings_contain_returns_section(self) -> None:
        cls = self._get_cls()
        for name in _GOOSE_METHODS:
            method = getattr(cls, name)
            doc = inspect.getdoc(method) or ""
            assert "Returns:" in doc or "Return" in doc, (
                f"GooseCLIHand.{name} docstring missing Returns section"
            )

    def test_methods_with_args_have_args_section(self) -> None:
        cls = self._get_cls()
        methods_with_params = (
            "_normalize_base_command",
            "_has_goose_builtin_flag",
            "_apply_backend_defaults",
            "_command_not_found_message",
            "_normalize_goose_provider",
            "_infer_goose_provider_from_model",
            "_normalize_ollama_host",
            "_resolve_ollama_host",
        )
        for name in methods_with_params:
            method = getattr(cls, name)
            doc = inspect.getdoc(method) or ""
            assert "Args:" in doc, f"GooseCLIHand.{name} docstring missing Args section"

    def test_build_subprocess_env_has_raises_section(self) -> None:
        cls = self._get_cls()
        doc = inspect.getdoc(cls._build_subprocess_env) or ""
        assert "Raises:" in doc


# ---------------------------------------------------------------------------
# 2. OpenCode CLI hand docstrings (5 methods) and _AUTH_ERROR_TOKENS constant
# ---------------------------------------------------------------------------


class TestOpenCodeDocstrings:
    """Verify OpenCodeCLIHand methods have Google-style docstrings."""

    def _get_cls(self):
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        return OpenCodeCLIHand

    def test_build_opencode_failure_message_has_docstring(self) -> None:
        doc = inspect.getdoc(self._get_cls()._build_opencode_failure_message)
        assert doc
        assert "Args:" in doc
        assert "Returns:" in doc

    def test_build_failure_message_has_docstring(self) -> None:
        doc = inspect.getdoc(self._get_cls()._build_failure_message)
        assert doc
        assert "Returns:" in doc

    def test_command_not_found_message_has_docstring(self) -> None:
        doc = inspect.getdoc(self._get_cls()._command_not_found_message)
        assert doc
        assert "Args:" in doc

    def test_invoke_opencode_has_docstring(self) -> None:
        doc = inspect.getdoc(self._get_cls()._invoke_opencode)
        assert doc
        assert "Args:" in doc

    def test_invoke_backend_has_docstring(self) -> None:
        doc = inspect.getdoc(self._get_cls()._invoke_backend)
        assert doc
        assert "Args:" in doc


class TestAuthErrorTokensConstant:
    """Verify _AUTH_ERROR_TOKENS module-level constant."""

    def test_constant_exists_and_is_tuple(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import _AUTH_ERROR_TOKENS

        assert isinstance(_AUTH_ERROR_TOKENS, tuple)

    def test_constant_has_expected_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import _AUTH_ERROR_TOKENS

        assert len(_AUTH_ERROR_TOKENS) == 5

    def test_all_tokens_are_lowercase_strings(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import _AUTH_ERROR_TOKENS

        for token in _AUTH_ERROR_TOKENS:
            assert isinstance(token, str)
            assert token == token.lower(), f"Token {token!r} is not lowercase"

    def test_unauthorized_in_tokens(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import _AUTH_ERROR_TOKENS

        assert "unauthorized" in _AUTH_ERROR_TOKENS

    def test_invalid_api_key_in_tokens(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import _AUTH_ERROR_TOKENS

        assert "invalid api key" in _AUTH_ERROR_TOKENS

    def test_constant_used_in_failure_message(self) -> None:
        """Auth error tokens should trigger the auth failure message."""
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        result = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="Error: 401 Unauthorized"
        )
        assert "authentication failed" in result.lower()

    def test_non_auth_error_uses_generic_message(self) -> None:
        """Non-auth errors should produce a generic failure message."""
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        result = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="Some other error occurred"
        )
        assert "exit=1" in result


# ---------------------------------------------------------------------------
# 3. E2E hand constants
# ---------------------------------------------------------------------------


class TestE2EConstants:
    """Verify E2E module-level constants extracted from inline strings."""

    def test_git_user_name_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_GIT_USER_NAME

        assert _E2E_GIT_USER_NAME == "helping-hands[bot]"

    def test_git_user_email_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_GIT_USER_EMAIL

        assert _E2E_GIT_USER_EMAIL == "helping-hands-bot@users.noreply.github.com"

    def test_commit_message_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_COMMIT_MESSAGE

        assert _E2E_COMMIT_MESSAGE == "test(e2e): minimal change from E2EHand"

    def test_pr_title_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_PR_TITLE

        assert _E2E_PR_TITLE == "test(e2e): minimal edit by helping_hands"

    def test_status_marker_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_STATUS_MARKER

        assert _E2E_STATUS_MARKER == "<!-- helping_hands:e2e-status -->"

    def test_status_marker_is_html_comment(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_STATUS_MARKER

        assert _E2E_STATUS_MARKER.startswith("<!--")
        assert _E2E_STATUS_MARKER.endswith("-->")

    def test_all_constants_are_strings(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import (
            _E2E_COMMIT_MESSAGE,
            _E2E_GIT_USER_EMAIL,
            _E2E_GIT_USER_NAME,
            _E2E_PR_TITLE,
            _E2E_STATUS_MARKER,
        )

        for const in (
            _E2E_GIT_USER_NAME,
            _E2E_GIT_USER_EMAIL,
            _E2E_COMMIT_MESSAGE,
            _E2E_PR_TITLE,
            _E2E_STATUS_MARKER,
        ):
            assert isinstance(const, str)
            assert const.strip(), f"Constant {const!r} is empty/whitespace"

    def test_marker_file_constant_unchanged(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_MARKER_FILE

        assert _E2E_MARKER_FILE == "HELPING_HANDS_E2E.md"


# ---------------------------------------------------------------------------
# 4. E2E hand docstrings (8 methods)
# ---------------------------------------------------------------------------

_E2E_METHODS = (
    "__init__",
    "_safe_repo_dir",
    "_work_base",
    "_configured_base_branch",
    "_build_e2e_pr_comment",
    "_build_e2e_pr_body",
    "run",
    "stream",
)


class TestE2EDocstrings:
    """Verify all E2EHand methods have Google-style docstrings."""

    def _get_cls(self):
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        return E2EHand

    def test_all_target_methods_have_docstrings(self) -> None:
        cls = self._get_cls()
        for name in _E2E_METHODS:
            method = getattr(cls, name)
            doc = inspect.getdoc(method)
            assert doc, f"E2EHand.{name} missing docstring"

    def test_methods_with_args_have_args_section(self) -> None:
        cls = self._get_cls()
        methods_with_params = (
            "__init__",
            "_safe_repo_dir",
            "_build_e2e_pr_comment",
            "_build_e2e_pr_body",
            "run",
            "stream",
        )
        for name in methods_with_params:
            method = getattr(cls, name)
            doc = inspect.getdoc(method) or ""
            assert "Args:" in doc, f"E2EHand.{name} docstring missing Args section"

    def test_run_has_raises_section(self) -> None:
        cls = self._get_cls()
        doc = inspect.getdoc(cls.run) or ""
        assert "Raises:" in doc

    def test_run_has_returns_section(self) -> None:
        cls = self._get_cls()
        doc = inspect.getdoc(cls.run) or ""
        assert "Returns:" in doc

    def test_stream_has_yields_section(self) -> None:
        cls = self._get_cls()
        doc = inspect.getdoc(cls.stream) or ""
        assert "Yields:" in doc
