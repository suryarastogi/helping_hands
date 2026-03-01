"""OpenAI provider wrapper."""

from __future__ import annotations

__all__ = ["OPENAI_PROVIDER", "OpenAIProvider"]

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider


class OpenAIProvider(AIProvider):
    """Wrapper around the OpenAI Python SDK client."""

    name = "openai"
    api_key_env_var = "OPENAI_API_KEY"
    default_model = "gpt-5.2"
    install_hint = "uv add openai"

    def _build_inner(self) -> Any:
        """Lazily construct an ``openai.OpenAI`` client.

        Uses ``OPENAI_API_KEY`` from the environment when available;
        otherwise falls back to the SDK's default auth resolution.
        """
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK is not installed. Install with: uv add openai"
            ) from exc

        api_key = os.environ.get(self.api_key_env_var)
        if api_key:
            return OpenAI(api_key=api_key)
        return OpenAI()

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        """Call the OpenAI Responses API via ``inner.responses.create``."""
        return inner.responses.create(
            model=model,
            input=messages,
            **kwargs,
        )


OPENAI_PROVIDER = OpenAIProvider()
