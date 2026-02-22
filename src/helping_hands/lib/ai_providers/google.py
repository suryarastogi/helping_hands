"""Google provider wrapper."""

from __future__ import annotations

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider


class GoogleProvider(AIProvider):
    """Wrapper around the Google GenAI Python SDK client."""

    name = "google"
    api_key_env_var = "GOOGLE_API_KEY"
    default_model = "gemini-2.0-flash"
    install_hint = "uv add google-genai"

    def _build_inner(self) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "Google GenAI SDK is not installed. Install with: uv add google-genai"
            ) from exc

        api_key = os.environ.get(self.api_key_env_var)
        if api_key:
            return genai.Client(api_key=api_key)
        return genai.Client()

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        contents = [m["content"] for m in messages if m["content"]]
        return inner.models.generate_content(
            model=model,
            contents=contents,
            **kwargs,
        )


GOOGLE_PROVIDER = GoogleProvider()
