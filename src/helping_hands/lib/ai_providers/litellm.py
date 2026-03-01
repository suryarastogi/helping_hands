"""LiteLLM provider wrapper."""

from __future__ import annotations

__all__ = ["LITELLM_PROVIDER", "LiteLLMProvider"]

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider


class LiteLLMProvider(AIProvider):
    """Wrapper around the LiteLLM Python package."""

    name = "litellm"
    api_key_env_var = "LITELLM_API_KEY"
    default_model = "gpt-5.2"
    install_hint = "uv add litellm"

    def _build_inner(self) -> Any:
        """Lazily import the ``litellm`` module and configure its API key.

        Sets ``litellm.api_key`` when ``LITELLM_API_KEY`` is in the
        environment. Returns the module itself as the inner client.
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
        """Call LiteLLM's unified ``completion`` function."""
        return inner.completion(
            model=model,
            messages=messages,
            **kwargs,
        )


LITELLM_PROVIDER = LiteLLMProvider()
