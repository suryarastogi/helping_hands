"""Ollama provider wrapper using the OpenAI-compatible API surface."""

from __future__ import annotations

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider

__all__ = ["OLLAMA_PROVIDER", "OllamaProvider"]


class OllamaProvider(AIProvider):
    """Wrapper around a local Ollama server via OpenAI-compatible client."""

    name = "ollama"
    api_key_env_var = "OLLAMA_API_KEY"
    default_model = "llama3.2:latest"
    install_hint = "uv add openai"
    base_url_env_var = "OLLAMA_BASE_URL"
    default_base_url = "http://localhost:11434/v1"

    def _build_inner(self) -> Any:
        """Construct an OpenAI-compatible client pointing at a local Ollama server.

        Reads the API key from ``OLLAMA_API_KEY`` (defaults to ``"ollama"``)
        and the base URL from ``OLLAMA_BASE_URL`` (defaults to
        ``http://localhost:11434/v1``).

        Returns:
            An ``openai.OpenAI`` client configured for the Ollama endpoint.

        Raises:
            RuntimeError: If the ``openai`` package is not installed.
        """
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK is not installed. Install with: uv add openai"
            ) from exc

        api_key = os.environ.get(self.api_key_env_var, "ollama").strip() or "ollama"
        base_url = (
            os.environ.get(self.base_url_env_var, self.default_base_url).strip()
            or self.default_base_url
        )
        return OpenAI(api_key=api_key, base_url=base_url)

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        """Send a completion request via the OpenAI-compatible chat completions API.

        Args:
            inner: The ``openai.OpenAI`` client pointing at the Ollama server.
            messages: Chat-style ``[{role, content}]`` message list.
            model: Ollama model identifier (e.g. ``"llama3.2:latest"``).
            **kwargs: Additional keyword arguments forwarded to
                ``inner.chat.completions.create()``.

        Returns:
            The raw chat completion response object.
        """
        return inner.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )


OLLAMA_PROVIDER = OllamaProvider()
