"""Enforce Google-style docstrings on all five AI providers, GitHubClient, and Hand base.

The AI provider interface (_build_inner, _complete_impl) is the extension point for
adding new LLM backends. Without documented Returns: and Raises: contracts on these
methods, implementors cannot know what exceptions callers expect to catch or what
the inner client object must look like, leading to silent runtime failures when a
new provider is added. Similarly, GitHubClient public methods are the sole layer
between the hands and the GitHub API, so their documented error contracts are
load-bearing. If these docstring checks regress, new provider authors lose the
structured guidance the codebase relies on to keep all implementations consistent.
"""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.ai_providers.anthropic import AnthropicProvider
from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.ai_providers.litellm import LiteLLMProvider
from helping_hands.lib.ai_providers.ollama import OllamaProvider
from helping_hands.lib.ai_providers.openai import OpenAIProvider
from helping_hands.lib.github import GitHubClient
from helping_hands.lib.hands.v1.hand.base import Hand

# ---------------------------------------------------------------------------
# AI provider method → expected sections mapping
# ---------------------------------------------------------------------------

_PROVIDER_METHODS: dict[str, list[str]] = {
    "_build_inner": ["Returns:", "Raises:"],
    "_complete_impl": ["Args:", "Returns:"],
}

_PROVIDER_CLASSES: list[type] = [
    AnthropicProvider,
    OpenAIProvider,
    GoogleProvider,
    LiteLLMProvider,
    OllamaProvider,
]


class TestProviderDocstrings:
    """Docstring presence and section checks for AI provider methods."""

    @pytest.mark.parametrize("cls", _PROVIDER_CLASSES, ids=lambda c: c.__name__)
    @pytest.mark.parametrize("method_name", list(_PROVIDER_METHODS.keys()))
    def test_docstring_exists(self, cls: type, method_name: str) -> None:
        method = getattr(cls, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"{cls.__name__}.{method_name} is missing a docstring"

    @pytest.mark.parametrize("cls", _PROVIDER_CLASSES, ids=lambda c: c.__name__)
    @pytest.mark.parametrize("method_name", list(_PROVIDER_METHODS.keys()))
    def test_docstring_non_trivial(self, cls: type, method_name: str) -> None:
        method = getattr(cls, method_name)
        doc = inspect.getdoc(method) or ""
        assert len(doc) > 30, (
            f"{cls.__name__}.{method_name} docstring is too short ({len(doc)} chars)"
        )

    @pytest.mark.parametrize(
        ("cls", "method_name", "sections"),
        [
            (cls, m, s)
            for cls in _PROVIDER_CLASSES
            for m, s in _PROVIDER_METHODS.items()
        ],
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_docstring_sections(
        self, cls: type, method_name: str, sections: list[str]
    ) -> None:
        method = getattr(cls, method_name)
        doc = inspect.getdoc(method) or ""
        for section in sections:
            assert section in doc, (
                f"{cls.__name__}.{method_name} docstring is missing '{section}'"
            )


# ---------------------------------------------------------------------------
# GitHub public method → expected sections mapping
# ---------------------------------------------------------------------------

_GITHUB_METHODS: dict[str, list[str]] = {
    "whoami": ["Returns:"],
    "get_pr": ["Args:", "Returns:", "Raises:"],
    "default_branch": ["Args:", "Returns:"],
    "update_pr_body": ["Args:", "Raises:"],
}


class TestGitHubDocstrings:
    """Docstring presence and section checks for GitHubClient public methods."""

    @pytest.mark.parametrize("method_name", list(_GITHUB_METHODS.keys()))
    def test_docstring_exists(self, method_name: str) -> None:
        method = getattr(GitHubClient, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"GitHubClient.{method_name} is missing a docstring"

    @pytest.mark.parametrize("method_name", list(_GITHUB_METHODS.keys()))
    def test_docstring_non_trivial(self, method_name: str) -> None:
        method = getattr(GitHubClient, method_name)
        doc = inspect.getdoc(method) or ""
        assert len(doc) > 30, (
            f"GitHubClient.{method_name} docstring is too short ({len(doc)} chars)"
        )

    @pytest.mark.parametrize(
        ("method_name", "sections"),
        list(_GITHUB_METHODS.items()),
    )
    def test_docstring_sections(self, method_name: str, sections: list[str]) -> None:
        method = getattr(GitHubClient, method_name)
        doc = inspect.getdoc(method) or ""
        for section in sections:
            assert section in doc, (
                f"GitHubClient.{method_name} docstring is missing '{section}'"
            )


# ---------------------------------------------------------------------------
# Hand base.py method → expected sections mapping
# ---------------------------------------------------------------------------

_HAND_METHODS: dict[str, list[str]] = {
    "__init__": ["Args:"],
    "_build_system_prompt": ["Returns:"],
    "_build_reference_repos_prompt_section": ["Returns:"],
    "interrupt": [],
    "reset_interrupt": [],
    "_use_native_git_auth_for_push": ["Args:", "Returns:"],
    "_push_noninteractive": ["Args:"],
}


class TestHandBaseDocstrings:
    """Docstring presence and section checks for Hand base.py methods."""

    @pytest.mark.parametrize("method_name", list(_HAND_METHODS.keys()))
    def test_docstring_exists(self, method_name: str) -> None:
        method = getattr(Hand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"Hand.{method_name} is missing a docstring"

    @pytest.mark.parametrize("method_name", list(_HAND_METHODS.keys()))
    def test_docstring_non_trivial(self, method_name: str) -> None:
        method = getattr(Hand, method_name)
        doc = inspect.getdoc(method) or ""
        assert len(doc) > 20, (
            f"Hand.{method_name} docstring is too short ({len(doc)} chars)"
        )

    @pytest.mark.parametrize(
        ("method_name", "sections"),
        [(m, s) for m, s in _HAND_METHODS.items() if s],
    )
    def test_docstring_sections(self, method_name: str, sections: list[str]) -> None:
        method = getattr(Hand, method_name)
        doc = inspect.getdoc(method) or ""
        for section in sections:
            assert section in doc, (
                f"Hand.{method_name} docstring is missing '{section}'"
            )
