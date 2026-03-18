"""Google provider wrapper."""

from __future__ import annotations

import os
from typing import Any

from helping_hands.lib.ai_providers.types import AIProvider

__all__ = ["GOOGLE_PROVIDER", "GoogleProvider"]


class GoogleProvider(AIProvider):
    """Wrapper around the Google GenAI Python SDK client."""

    name = "google"
    api_key_env_var = "GOOGLE_API_KEY"
    default_model = "gemini-2.0-flash"
    install_hint = "uv add google-genai"

    def _build_inner(self) -> Any:
        """Construct the Google GenAI SDK client.

        Reads the API key from the ``GOOGLE_API_KEY`` environment variable.
        If the variable is not set, the client is created without an explicit
        key (relying on SDK-level defaults such as ADC).

        Returns:
            A ``google.genai.Client`` instance.

        Raises:
            RuntimeError: If the ``google-genai`` package is not installed.
        """
        sdk = self._require_sdk("google.genai")
        genai = sdk

        api_key = os.environ.get(self.api_key_env_var, "").strip()
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
        """Send a completion request via the Google GenAI content generation API.

        Extracts non-empty ``content`` values from *messages* and passes them
        as the ``contents`` parameter.

        Args:
            inner: The ``google.genai.Client`` instance.
            messages: Chat-style ``[{role, content}]`` message list.
            model: Google model identifier (e.g. ``"gemini-2.0-flash"``).
            **kwargs: Additional keyword arguments forwarded to
                ``inner.models.generate_content()``.

        Returns:
            The raw Google GenAI response object.
        """
        contents = [m.get("content") for m in messages if m.get("content")]
        if not contents:
            raise ValueError(
                "all messages have empty content — nothing to send to Google"
            )
        return inner.models.generate_content(
            model=model,
            contents=contents,
            **kwargs,
        )


GOOGLE_PROVIDER = GoogleProvider()
