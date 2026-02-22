"""Anthropic provider wrapper."""

from __future__ import annotations

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider


class AnthropicProvider(AIProvider):
    """Wrapper around the Anthropic Python SDK client."""

    name = "anthropic"
    api_key_env_var = "ANTHROPIC_API_KEY"
    default_model = "claude-3-5-sonnet-latest"
    install_hint = "uv add anthropic"

    def _build_inner(self) -> Any:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Anthropic SDK is not installed. Install with: uv add anthropic"
            ) from exc

        api_key = os.environ.get(self.api_key_env_var)
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
        max_tokens = kwargs.pop("max_tokens", 1024)
        return inner.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            **kwargs,
        )


ANTHROPIC_PROVIDER = AnthropicProvider()
