"""Tests for v161: __all__ exports for hand, CLI hand, server, and CLI entry modules."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# hands/v1/hand/base.py __all__ tests
# ---------------------------------------------------------------------------
class TestHandBaseAllExport:
    """Verify base.py __all__ declaration."""

    def test_all_contains_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import __all__

        assert "Hand" in __all__

    def test_all_contains_hand_response(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import __all__

        assert "HandResponse" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.base as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import __all__

        assert len(__all__) == 3


# ---------------------------------------------------------------------------
# hands/v1/hand/e2e.py __all__ tests
# ---------------------------------------------------------------------------
class TestE2EHandAllExport:
    """Verify e2e.py __all__ declaration."""

    def test_all_contains_e2e_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import __all__

        assert "E2EHand" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.e2e as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# hands/v1/hand/iterative.py __all__ tests
# ---------------------------------------------------------------------------
class TestIterativeHandAllExport:
    """Verify iterative.py __all__ declaration."""

    def test_all_contains_basic_langgraph_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import __all__

        assert "BasicLangGraphHand" in __all__

    def test_all_contains_basic_atomic_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import __all__

        assert "BasicAtomicHand" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.iterative as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# hands/v1/hand/cli/claude.py __all__ tests
# ---------------------------------------------------------------------------
class TestClaudeCodeHandAllExport:
    """Verify claude.py __all__ declaration."""

    def test_all_contains_claude_code_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import __all__

        assert "ClaudeCodeHand" in __all__

    def test_all_has_expected_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import __all__

        private = sorted(name for name in __all__ if name.startswith("_"))
        assert private == ["_TOOL_SUMMARY_KEY_MAP", "_TOOL_SUMMARY_STATIC"]

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.claude as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import __all__

        assert len(__all__) == 3


# ---------------------------------------------------------------------------
# hands/v1/hand/cli/codex.py __all__ tests
# ---------------------------------------------------------------------------
class TestCodexCLIHandAllExport:
    """Verify codex.py __all__ declaration."""

    def test_all_contains_codex_cli_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import __all__

        assert "CodexCLIHand" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.codex as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# hands/v1/hand/cli/gemini.py __all__ tests
# ---------------------------------------------------------------------------
class TestGeminiCLIHandAllExport:
    """Verify gemini.py __all__ declaration."""

    def test_all_contains_gemini_cli_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import __all__

        assert "GeminiCLIHand" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.gemini as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# hands/v1/hand/cli/goose.py __all__ tests
# ---------------------------------------------------------------------------
class TestGooseCLIHandAllExport:
    """Verify goose.py __all__ declaration."""

    def test_all_contains_goose_cli_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import __all__

        assert "GooseCLIHand" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.goose as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# hands/v1/hand/cli/opencode.py __all__ tests
# ---------------------------------------------------------------------------
class TestOpenCodeCLIHandAllExport:
    """Verify opencode.py __all__ declaration."""

    def test_all_contains_opencode_cli_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import __all__

        assert "OpenCodeCLIHand" in __all__

    def test_all_has_expected_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == ["_PROVIDER_ENV_MAP"]

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.opencode as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# hands/v1/hand/cli/docker_sandbox_claude.py __all__ tests
# ---------------------------------------------------------------------------
class TestDockerSandboxClaudeCodeHandAllExport:
    """Verify docker_sandbox_claude.py __all__ declaration."""

    def test_all_contains_docker_sandbox_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import __all__

        assert "DockerSandboxClaudeCodeHand" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# server/app.py __all__ tests
# ---------------------------------------------------------------------------
class TestServerAppAllExport:
    """Verify server/app.py __all__ declaration."""

    def test_all_contains_app(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        assert "app" in __all__

    def test_all_contains_build_request(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        assert "BuildRequest" in __all__

    def test_all_contains_build_response(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        assert "BuildResponse" in __all__

    def test_all_contains_task_status(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        assert "TaskStatus" in __all__

    def test_all_contains_task_cancel_response(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        assert "TaskCancelResponse" in __all__

    def test_all_has_no_private_names(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        pytest.importorskip("fastapi")
        import helping_hands.server.app as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        assert len(__all__) == 18


# ---------------------------------------------------------------------------
# server/celery_app.py __all__ tests
# ---------------------------------------------------------------------------
class TestCeleryAppAllExport:
    """Verify server/celery_app.py __all__ declaration."""

    def test_all_contains_celery_app(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import __all__

        assert "celery_app" in __all__

    def test_all_contains_build_feature(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import __all__

        assert "build_feature" in __all__

    def test_all_has_no_private_names(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        pytest.importorskip("celery")
        import helping_hands.server.celery_app as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# server/mcp_server.py __all__ tests
# ---------------------------------------------------------------------------
class TestMcpServerAllExport:
    """Verify server/mcp_server.py __all__ declaration."""

    def test_all_contains_mcp(self) -> None:
        pytest.importorskip("mcp")
        from helping_hands.server.mcp_server import __all__

        assert "mcp" in __all__

    def test_all_contains_main(self) -> None:
        pytest.importorskip("mcp")
        from helping_hands.server.mcp_server import __all__

        assert "main" in __all__

    def test_all_has_no_private_names(self) -> None:
        pytest.importorskip("mcp")
        from helping_hands.server.mcp_server import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        pytest.importorskip("mcp")
        import helping_hands.server.mcp_server as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        pytest.importorskip("mcp")
        from helping_hands.server.mcp_server import __all__

        assert len(__all__) == 2


# ---------------------------------------------------------------------------
# cli/main.py __all__ tests
# ---------------------------------------------------------------------------
class TestCliMainAllExport:
    """Verify cli/main.py __all__ declaration."""

    def test_all_contains_build_parser(self) -> None:
        from helping_hands.cli.main import __all__

        assert "build_parser" in __all__

    def test_all_contains_main(self) -> None:
        from helping_hands.cli.main import __all__

        assert "main" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.cli.main import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.cli.main as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.cli.main import __all__

        assert len(__all__) == 2
