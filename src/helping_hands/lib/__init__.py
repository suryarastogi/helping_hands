"""Core library: configuration, repo/git handling, hands, and providers.

Primary namespaces:
- ``helping_hands.lib.hands`` for backend implementations.
- ``helping_hands.lib.ai_providers`` for provider wrappers and defaults.
- ``helping_hands.lib.meta`` for shared cross-cutting tooling.
"""

__all__ = [
    "ai_providers",
    "config",
    "default_prompts",
    "github",
    "github_url",
    "hands",
    "meta",
    "repo",
    "validation",
]
