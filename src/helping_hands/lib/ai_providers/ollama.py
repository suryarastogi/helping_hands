"""Ollama provider wrapper using the OpenAI-compatible API surface."""

from __future__ import annotations

__all__ = ["OLLAMA_PROVIDER", "OllamaProvider"]

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider


class OllamaProvider(AIProvider):
    """Wrapper around a local Ollama server via OpenAI-compatible client.

    Attributes:
        base_url_env_var: Environment variable that overrides the Ollama
            server URL (default ``OLLAMA_BASE_URL``).
        default_base_url: Fallback URL when ``base_url_env_var`` is unset
            (default ``http://localhost:11434/v1``).
    """

    name = "ollama"
    api_key_env_var = "OLLAMA_API_KEY"
    default_model = "llama3.2:latest"
    install_hint = "uv add openai"
    base_url_env_var = "OLLAMA_BASE_URL"
    default_base_url = "http://localhost:11434/v1"

    def _build_inner(self) -> Any:
        """Lazily construct an ``openai.OpenAI`` client pointing at Ollama.

        Uses ``OLLAMA_BASE_URL`` (default ``http://localhost:11434/v1``)
        and ``OLLAMA_API_KEY`` (default ``"ollama"``) for local server auth.
        """
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK is not installed. Install with: uv add openai"
            ) from exc

        api_key = os.environ.get(self.api_key_env_var, "ollama")
        base_url = os.environ.get(self.base_url_env_var, self.default_base_url)
        return OpenAI(api_key=api_key, base_url=base_url)

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        """Call Ollama via the OpenAI-compatible Chat Completions API."""
        return inner.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )


OLLAMA_PROVIDER = OllamaProvider()
