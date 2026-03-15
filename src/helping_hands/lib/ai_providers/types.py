"""Shared provider wrapper interface and helpers.

The classes in ``helping_hands.lib.ai_providers`` are thin wrappers around
provider-specific SDK clients. They expose a common interface while still
allowing backend-specific access via ``provider.inner``.
"""

from __future__ import annotations

import abc
import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = ["AIProvider", "PromptInput", "normalize_messages"]

PromptInput = str | Sequence[Mapping[str, str]]


def normalize_messages(prompt_or_messages: PromptInput) -> list[dict[str, str]]:
    """Normalize caller input into chat-style ``[{role, content}]`` messages.

    Args:
        prompt_or_messages: Either a plain string (wrapped as a single user
            message) or a sequence of mapping objects with ``role`` and
            ``content`` keys.

    Returns:
        A list of ``{"role": ..., "content": ...}`` dicts ready for provider
        completion calls.

    Raises:
        TypeError: If any element in a sequence input is not a
            :class:`~collections.abc.Mapping`.
    """
    if isinstance(prompt_or_messages, str):
        return [{"role": "user", "content": prompt_or_messages}]

    normalized: list[dict[str, str]] = []
    for idx, msg in enumerate(prompt_or_messages):
        if not isinstance(msg, Mapping):
            raise TypeError(
                f"Expected a Mapping for message at index {idx}, "
                f"got {type(msg).__name__}"
            )
        role = str(msg.get("role", "user"))
        raw_content = msg.get("content", "")
        if raw_content is not None and not isinstance(raw_content, str):
            raise TypeError(
                f"Expected str or None for 'content' at message index {idx}, "
                f"got {type(raw_content).__name__}"
            )
        content = raw_content or ""
        normalized.append({"role": role, "content": content})
    return normalized


class AIProvider(abc.ABC):
    """Common provider wrapper interface with lazy inner client loading."""

    name: str
    api_key_env_var: str
    default_model: str

    def __init__(self, *, inner: Any | None = None) -> None:
        self._inner = inner

    @property
    def inner(self) -> Any:
        """Provider-specific underlying SDK object."""
        if self._inner is None:
            self._inner = self._build_inner()
        return self._inner

    @property
    @abc.abstractmethod
    def install_hint(self) -> str:
        """Human-readable dependency install hint."""

    @abc.abstractmethod
    def _build_inner(self) -> Any:
        """Construct the provider-specific SDK client/module."""

    @abc.abstractmethod
    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        """Provider-specific completion call implementation."""

    def complete(
        self,
        prompt_or_messages: PromptInput,
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run a completion call using the provider-specific implementation."""
        messages = normalize_messages(prompt_or_messages)
        resolved_model = model or self.default_model
        if not resolved_model or not resolved_model.strip():
            raise ValueError(
                "No model specified and no default_model configured on the provider."
            )
        if not any(m.get("content") for m in messages):
            raise ValueError(
                "all messages have empty content; cannot send empty request"
            )
        return self._complete_impl(
            inner=self.inner,
            messages=messages,
            model=resolved_model,
            **kwargs,
        )

    async def acomplete(
        self,
        prompt_or_messages: PromptInput,
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Async completion wrapper around ``complete``."""
        return await asyncio.to_thread(
            self.complete,
            prompt_or_messages,
            model=model,
            **kwargs,
        )
