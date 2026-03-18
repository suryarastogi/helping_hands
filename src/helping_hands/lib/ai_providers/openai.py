"""OpenAI provider wrapper."""

from __future__ import annotations

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider

__all__ = ["OPENAI_PROVIDER", "OpenAIProvider"]


class OpenAIProvider(AIProvider):
    """Wrapper around the OpenAI Python SDK client."""

    name = "openai"
    api_key_env_var = "OPENAI_API_KEY"
    default_model = "gpt-5.2"
    install_hint = "uv add openai"

    def _build_inner(self) -> Any:
        """Construct the OpenAI SDK client.

        Reads the API key from the ``OPENAI_API_KEY`` environment variable.
        If the variable is not set, the client is created without an explicit
        key (relying on SDK-level defaults).

        Returns:
            An ``openai.OpenAI`` client instance.

        Raises:
            RuntimeError: If the ``openai`` package is not installed.
        """
        sdk = self._require_sdk("openai")

        api_key = os.environ.get(self.api_key_env_var, "").strip()
        if api_key:
            return sdk.OpenAI(api_key=api_key)
        return sdk.OpenAI()

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        """Send a completion request via the OpenAI Responses API.

        Args:
            inner: The ``openai.OpenAI`` client instance.
            messages: Chat-style ``[{role, content}]`` message list.
            model: OpenAI model identifier (e.g. ``"gpt-5.2"``).
            **kwargs: Additional keyword arguments forwarded to
                ``inner.responses.create()``.

        Returns:
            The raw OpenAI API response object.
        """
        return inner.responses.create(
            model=model,
            input=messages,
            **kwargs,
        )


OPENAI_PROVIDER = OpenAIProvider()
