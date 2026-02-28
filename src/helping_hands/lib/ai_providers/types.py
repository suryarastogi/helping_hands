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

PromptInput = str | Sequence[Mapping[str, str]]


def normalize_messages(prompt_or_messages: PromptInput) -> list[dict[str, str]]:
    """Normalize caller input into chat-style ``[{role, content}]`` messages."""
    if isinstance(prompt_or_messages, str):
        return [{"role": "user", "content": prompt_or_messages}]

    normalized: list[dict[str, str]] = []
    for msg in prompt_or_messages:
        role = str(msg.get("role", "user"))
        content = str(msg.get("content", ""))
        normalized.append({"role": role, "content": content})
    return normalized


class AIProvider(abc.ABC):
    """Common provider wrapper interface with lazy inner client loading."""

    name: str
    api_key_env_var: str
    default_model: str

    def __init__(self, *, inner: Any | None = None) -> None:
        """Initialise a provider wrapper.

        Args:
            inner: Pre-built SDK client. When ``None`` (default), the client
                is lazily constructed on first access via ``_build_inner``.
        """
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
