"""LiteLLM provider wrapper."""

from __future__ import annotations

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider

__all__ = ["LITELLM_PROVIDER", "LiteLLMProvider"]


class LiteLLMProvider(AIProvider):
    """Wrapper around the LiteLLM Python package."""

    name = "litellm"
    api_key_env_var = "LITELLM_API_KEY"
    default_model = "gpt-5.2"
    install_hint = "uv add litellm"

    def _build_inner(self) -> Any:
        """Import and configure the LiteLLM module.

        Reads the API key from the ``LITELLM_API_KEY`` environment variable
        and sets it on the ``litellm`` module if present.

        Returns:
            The ``litellm`` module itself (used as a callable namespace).

        Raises:
            RuntimeError: If the ``litellm`` package is not installed.
        """
        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError(
                "LiteLLM is not installed. Install with: uv add litellm"
            ) from exc

        api_key = os.environ.get(self.api_key_env_var)
        if api_key:
            litellm.api_key = api_key
        return litellm

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        """Send a completion request via LiteLLM's unified completion interface.

        Args:
            inner: The ``litellm`` module.
            messages: Chat-style ``[{role, content}]`` message list.
            model: Model identifier in LiteLLM format (e.g. ``"gpt-5.2"``).
            **kwargs: Additional keyword arguments forwarded to
                ``inner.completion()``.

        Returns:
            The raw LiteLLM response object.
        """
        return inner.completion(
            model=model,
            messages=messages,
            **kwargs,
        )


LITELLM_PROVIDER = LiteLLMProvider()
