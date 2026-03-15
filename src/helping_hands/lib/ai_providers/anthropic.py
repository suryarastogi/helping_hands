"""Anthropic provider wrapper."""

from __future__ import annotations

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider

__all__ = ["ANTHROPIC_PROVIDER", "AnthropicProvider"]

_DEFAULT_MAX_TOKENS = 1024
"""Default ``max_tokens`` for Anthropic completions when not specified."""


class AnthropicProvider(AIProvider):
    """Wrapper around the Anthropic Python SDK client."""

    name = "anthropic"
    api_key_env_var = "ANTHROPIC_API_KEY"
    default_model = "claude-3-5-sonnet-latest"
    install_hint = "uv add anthropic"

    def _build_inner(self) -> Any:
        """Construct the Anthropic SDK client.

        Reads the API key from the ``ANTHROPIC_API_KEY`` environment variable.
        If the variable is not set, the client is created without an explicit
        key (relying on SDK-level defaults).

        Returns:
            An ``anthropic.Anthropic`` client instance.

        Raises:
            RuntimeError: If the ``anthropic`` package is not installed.
        """
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                f"Anthropic SDK is not installed. Install with: {self.install_hint}"
            ) from exc

        api_key = os.environ.get(self.api_key_env_var, "").strip()
        if api_key:
            return Anthropic(api_key=api_key)
        return Anthropic()

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        """Send a completion request via the Anthropic Messages API.

        Args:
            inner: The ``anthropic.Anthropic`` client instance.
            messages: Chat-style ``[{role, content}]`` message list.
            model: Anthropic model identifier (e.g. ``"claude-3-5-sonnet-latest"``).
            **kwargs: Additional keyword arguments forwarded to
                ``inner.messages.create()``.  ``max_tokens`` defaults to
                :data:`_DEFAULT_MAX_TOKENS` if not provided.

        Returns:
            The raw Anthropic API response object.
        """
        max_tokens = kwargs.pop("max_tokens", _DEFAULT_MAX_TOKENS)
        return inner.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            **kwargs,
        )


ANTHROPIC_PROVIDER = AnthropicProvider()
