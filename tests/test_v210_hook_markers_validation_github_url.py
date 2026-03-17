"""Tests for v210 — hook failure markers constant, validation + github_url coverage.

Covers:
- _GIT_HOOK_FAILURE_MARKERS constant in base.py
- _is_git_hook_failure uses the module-level constant (not inline)
- validation.py __all__ contract
- github_url.py __all__ contract
"""

from __future__ import annotations

import inspect

from helping_hands.lib import (
    github_url as github_url_module,
    validation as validation_module,
)
from helping_hands.lib.hands.v1.hand import base as hand_base_module

# ---------------------------------------------------------------------------
# _GIT_HOOK_FAILURE_MARKERS constant
# ---------------------------------------------------------------------------


class TestGitHookFailureMarkers:
    """Tests for the extracted _GIT_HOOK_FAILURE_MARKERS constant."""

    def test_constant_exists(self) -> None:
        assert hasattr(hand_base_module, "_GIT_HOOK_FAILURE_MARKERS")

    def test_is_tuple(self) -> None:
        assert isinstance(hand_base_module._GIT_HOOK_FAILURE_MARKERS, tuple)

    def test_has_expected_entries(self) -> None:
        markers = hand_base_module._GIT_HOOK_FAILURE_MARKERS
        expected = {
            "husky -",
            "husky:",
            "lint-staged",
            "pre-commit hook",
            "hook failed",
            "eslint found",
            "eslint:",
            "prettier",
        }
        assert set(markers) == expected

    def test_all_entries_are_lowercase(self) -> None:
        for marker in hand_base_module._GIT_HOOK_FAILURE_MARKERS:
            assert marker == marker.lower(), f"{marker!r} is not lowercase"

    def test_all_entries_are_strings(self) -> None:
        for marker in hand_base_module._GIT_HOOK_FAILURE_MARKERS:
            assert isinstance(marker, str)

    def test_not_empty(self) -> None:
        assert len(hand_base_module._GIT_HOOK_FAILURE_MARKERS) > 0

    def test_is_git_hook_failure_uses_constant(self) -> None:
        """Verify _is_git_hook_failure references the module-level constant."""
        source = inspect.getsource(hand_base_module.Hand._is_git_hook_failure)
        assert "_GIT_HOOK_FAILURE_MARKERS" in source

    def test_each_marker_triggers_detection(self) -> None:
        """Each marker in the constant should trigger hook failure detection."""
        for marker in hand_base_module._GIT_HOOK_FAILURE_MARKERS:
            msg = f"error: {marker} something failed"
            assert hand_base_module.Hand._is_git_hook_failure(msg) is True, (
                f"marker {marker!r} did not trigger detection"
            )

    def test_no_false_positive(self) -> None:
        assert hand_base_module.Hand._is_git_hook_failure("normal error") is False


# ---------------------------------------------------------------------------
# validation.py module contract
# ---------------------------------------------------------------------------


class TestValidationModuleContract:
    """Verify validation module's public API surface."""

    def test_all_exports(self) -> None:
        assert set(validation_module.__all__) == {
            "require_non_empty_string",
            "require_positive_float",
            "require_positive_int",
        }

    def test_all_exports_are_callable(self) -> None:
        for name in validation_module.__all__:
            assert callable(getattr(validation_module, name))

    def test_has_docstring(self) -> None:
        assert validation_module.__doc__


# ---------------------------------------------------------------------------
# github_url.py module contract
# ---------------------------------------------------------------------------


class TestGithubUrlModuleContract:
    """Verify github_url module's public API surface."""

    def test_all_exports(self) -> None:
        assert set(github_url_module.__all__) == {
            "DEFAULT_CLONE_ERROR_MSG",
            "ENV_GCM_INTERACTIVE",
            "ENV_GIT_TERMINAL_PROMPT",
            "GITHUB_HOSTNAME",
            "GITHUB_TOKEN_USER",
            "GIT_CLONE_TIMEOUT_S",
            "build_clone_url",
            "noninteractive_env",
            "redact_credentials",
            "repo_tmp_dir",
            "resolve_github_token",
            "validate_repo_spec",
        }

    def test_all_exports_resolve(self) -> None:
        for name in github_url_module.__all__:
            assert hasattr(github_url_module, name)

    def test_has_docstring(self) -> None:
        assert github_url_module.__doc__

    def test_functions_have_docstrings(self) -> None:
        for name in github_url_module.__all__:
            obj = getattr(github_url_module, name)
            if callable(obj):
                assert obj.__doc__, f"{name} missing docstring"
