"""Provider wrapper layer for AI backends used by hands.

This package sits alongside ``helping_hands.lib.hands`` and provides a stable
namespace for provider-specific wrappers and defaults.

Related interfaces:
- Used by hand/backends that need provider-level invocation and defaults.
- Referenced by CLI/server code to resolve provider implementations.
"""

from helping_hands.lib.ai_providers.anthropic import (
    ANTHROPIC_PROVIDER,
    AnthropicProvider,
)
from helping_hands.lib.ai_providers.google import GOOGLE_PROVIDER, GoogleProvider
from helping_hands.lib.ai_providers.litellm import LITELLM_PROVIDER, LiteLLMProvider
from helping_hands.lib.ai_providers.openai import OPENAI_PROVIDER, OpenAIProvider
from helping_hands.lib.ai_providers.types import AIProvider

PROVIDERS: dict[str, AIProvider] = {
    OPENAI_PROVIDER.name: OPENAI_PROVIDER,
    ANTHROPIC_PROVIDER.name: ANTHROPIC_PROVIDER,
    GOOGLE_PROVIDER.name: GOOGLE_PROVIDER,
    LITELLM_PROVIDER.name: LITELLM_PROVIDER,
}

__all__ = [
    "ANTHROPIC_PROVIDER",
    "GOOGLE_PROVIDER",
    "LITELLM_PROVIDER",
    "OPENAI_PROVIDER",
    "PROVIDERS",
    "AIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "LiteLLMProvider",
    "OpenAIProvider",
]
