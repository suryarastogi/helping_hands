"""Tests for v159: __all__ exports for AI providers, pr_description, model_provider, schedules."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# openai.py __all__ tests
# ---------------------------------------------------------------------------
class TestOpenAIProviderAllExport:
    """Verify openai.py __all__ declaration."""

    def test_all_contains_openai_provider(self) -> None:
        from helping_hands.lib.ai_providers.openai import __all__

        assert "OpenAIProvider" in __all__

    def test_all_contains_openai_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.openai import __all__

        assert "OPENAI_PROVIDER" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.ai_providers.openai import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.ai_providers.openai as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.ai_providers.openai import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# anthropic.py __all__ tests
# ---------------------------------------------------------------------------
class TestAnthropicProviderAllExport:
    """Verify anthropic.py __all__ declaration."""

    def test_all_contains_anthropic_provider(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import __all__

        assert "AnthropicProvider" in __all__

    def test_all_contains_anthropic_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import __all__

        assert "ANTHROPIC_PROVIDER" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.ai_providers.anthropic as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# google.py __all__ tests
# ---------------------------------------------------------------------------
class TestGoogleProviderAllExport:
    """Verify google.py __all__ declaration."""

    def test_all_contains_google_provider(self) -> None:
        from helping_hands.lib.ai_providers.google import __all__

        assert "GoogleProvider" in __all__

    def test_all_contains_google_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.google import __all__

        assert "GOOGLE_PROVIDER" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.ai_providers.google import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.ai_providers.google as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.ai_providers.google import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# litellm.py __all__ tests
# ---------------------------------------------------------------------------
class TestLiteLLMProviderAllExport:
    """Verify litellm.py __all__ declaration."""

    def test_all_contains_litellm_provider(self) -> None:
        from helping_hands.lib.ai_providers.litellm import __all__

        assert "LiteLLMProvider" in __all__

    def test_all_contains_litellm_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.litellm import __all__

        assert "LITELLM_PROVIDER" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.ai_providers.litellm import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.ai_providers.litellm as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.ai_providers.litellm import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# ollama.py __all__ tests
# ---------------------------------------------------------------------------
class TestOllamaProviderAllExport:
    """Verify ollama.py __all__ declaration."""

    def test_all_contains_ollama_provider(self) -> None:
        from helping_hands.lib.ai_providers.ollama import __all__

        assert "OllamaProvider" in __all__

    def test_all_contains_ollama_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.ollama import __all__

        assert "OLLAMA_PROVIDER" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.ai_providers.ollama import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.ai_providers.ollama as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.ai_providers.ollama import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# pr_description.py __all__ tests
# ---------------------------------------------------------------------------
class TestPRDescriptionAllExport:
    """Verify pr_description.py __all__ declaration."""

    def test_all_contains_pr_description(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import __all__

        assert "PRDescription" in __all__

    def test_all_contains_generate_pr_description(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import __all__

        assert "generate_pr_description" in __all__

    def test_all_contains_generate_commit_message(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import __all__

        assert "generate_commit_message" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.pr_description as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import __all__

        assert len(__all__) == 3


# ---------------------------------------------------------------------------
# model_provider.py __all__ tests
# ---------------------------------------------------------------------------
class TestModelProviderAllExport:
    """Verify model_provider.py __all__ declaration."""

    def test_all_contains_hand_model(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import __all__

        assert "HandModel" in __all__

    def test_all_contains_resolve_hand_model(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import __all__

        assert "resolve_hand_model" in __all__

    def test_all_contains_build_langchain_chat_model(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import __all__

        assert "build_langchain_chat_model" in __all__

    def test_all_contains_build_atomic_client(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import __all__

        assert "build_atomic_client" in __all__

    def test_all_has_no_unexpected_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import __all__

        allowed_private = {
            "_PROVIDER_OPENAI",
            "_PROVIDER_ANTHROPIC",
            "_PROVIDER_GOOGLE",
            "_PROVIDER_OLLAMA",
            "_PROVIDER_LITELLM",
            "_require_langchain_class",
        }
        private = [
            name
            for name in __all__
            if name.startswith("_") and name not in allowed_private
        ]
        assert private == [], f"Unexpected private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.model_provider as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import __all__

        assert len(__all__) == 11


# ---------------------------------------------------------------------------
# schedules.py __all__ tests
# ---------------------------------------------------------------------------


class TestSchedulesAllExport:
    """Verify schedules.py __all__ declaration."""

    def test_all_contains_scheduled_task(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert "ScheduledTask" in __all__

    def test_all_contains_cron_presets(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert "CRON_PRESETS" in __all__

    def test_all_contains_validate_cron_expression(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert "validate_cron_expression" in __all__

    def test_all_contains_next_run_time(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert "next_run_time" in __all__

    def test_all_contains_generate_schedule_id(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert "generate_schedule_id" in __all__

    def test_all_contains_schedule_manager(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert "ScheduleManager" in __all__

    def test_all_contains_get_schedule_manager(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert "get_schedule_manager" in __all__

    def test_all_has_no_private_names(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        pytest.importorskip("celery")
        import helping_hands.server.schedules as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import __all__

        assert len(__all__) == 7
