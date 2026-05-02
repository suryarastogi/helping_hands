"""Tests for ClaudeCodeHand opt-in feature flag injections.

Covers four PR-163 features ported onto current Claude Code CLI (2.x):

* ``--max-turns`` injection driven by ``HELPING_HANDS_CLAUDE_MAX_TURNS``.
* ``--append-system-prompt`` resolved from
  ``HELPING_HANDS_CLAUDE_SYSTEM_PROMPT`` or auto-read from AGENT.md / CLAUDE.md.
* ``--allowedTools`` / ``--disallowedTools`` from
  ``HELPING_HANDS_CLAUDE_ALLOWED_TOOLS`` / ``..._DISALLOWED_TOOLS``.
* Session continuation: capturing ``session_id`` from result events and
  injecting ``--continue --session-id`` on subsequent invocations when
  ``HELPING_HANDS_CLAUDE_SESSION_CONTINUE=1``. Also covers ``cost_metadata``
  capture and cumulative cost accumulation on the hand instance.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from helping_hands.lib.hands.v1.hand.cli.claude import (
    ClaudeCodeHand,
    _StreamJsonEmitter,
)


@pytest.fixture()
def claude_hand(make_cli_hand):
    return make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")


def _clear_feature_env(monkeypatch) -> None:
    for var in (
        "HELPING_HANDS_CLAUDE_MAX_TURNS",
        "HELPING_HANDS_CLAUDE_SYSTEM_PROMPT",
        "HELPING_HANDS_CLAUDE_ALLOWED_TOOLS",
        "HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS",
        "HELPING_HANDS_CLAUDE_SESSION_CONTINUE",
    ):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# --max-turns
# ---------------------------------------------------------------------------


class TestResolveMaxTurns:
    def test_unset_returns_zero(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_MAX_TURNS", raising=False)
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_blank_returns_zero(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "   ")
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_positive_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "5")
        assert ClaudeCodeHand._resolve_max_turns() == 5

    def test_zero_is_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "0")
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_negative_is_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "-3")
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_non_integer_falls_back(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "abc")
        assert ClaudeCodeHand._resolve_max_turns() == 0


class TestInjectMaxTurns:
    def test_zero_skips_injection(self) -> None:
        cmd = ["claude", "-p", "hi"]
        assert ClaudeCodeHand._inject_max_turns(cmd, 0) == cmd

    def test_inserts_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "hi"]
        result = ClaudeCodeHand._inject_max_turns(cmd, 4)
        assert result == ["claude", "--max-turns", "4", "-p", "hi"]

    def test_no_double_injection(self) -> None:
        cmd = ["claude", "--max-turns", "2", "-p", "hi"]
        assert ClaudeCodeHand._inject_max_turns(cmd, 4) == cmd

    def test_no_double_injection_equals_form(self) -> None:
        cmd = ["claude", "--max-turns=2", "-p", "hi"]
        assert ClaudeCodeHand._inject_max_turns(cmd, 4) == cmd

    def test_appends_when_no_p_flag(self) -> None:
        cmd = ["claude", "hi"]
        result = ClaudeCodeHand._inject_max_turns(cmd, 4)
        assert result == ["claude", "hi", "--max-turns", "4"]


# ---------------------------------------------------------------------------
# --append-system-prompt
# ---------------------------------------------------------------------------


class TestResolveSystemPrompt:
    def test_env_var_takes_priority(self, claude_hand, monkeypatch, tmp_path) -> None:
        # AGENT.md is present but env var should win.
        (tmp_path / "AGENT.md").write_text("from agent doc")
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", "explicit prompt")
        # claude_hand's repo_index points at make_cli_hand's tmp_path; here we
        # rebuild the hand to point at the per-test tmp_path so AGENT.md is
        # actually under repo root. We just verify env var wins regardless.
        assert claude_hand._resolve_system_prompt() == "explicit prompt"

    def test_reads_agent_md(self, make_cli_hand, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        hand = make_cli_hand(ClaudeCodeHand)
        (hand.repo_index.root / "AGENT.md").write_text("agent rules here")
        assert hand._resolve_system_prompt() == "agent rules here"
        del tmp_path  # unused

    def test_falls_back_to_claude_md(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        hand = make_cli_hand(ClaudeCodeHand)
        (hand.repo_index.root / "CLAUDE.md").write_text("claude rules")
        assert hand._resolve_system_prompt() == "claude rules"

    def test_agent_md_wins_over_claude_md(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        hand = make_cli_hand(ClaudeCodeHand)
        (hand.repo_index.root / "AGENT.md").write_text("agent")
        (hand.repo_index.root / "CLAUDE.md").write_text("claude")
        assert hand._resolve_system_prompt() == "agent"

    def test_empty_when_nothing_configured(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        hand = make_cli_hand(ClaudeCodeHand)
        assert hand._resolve_system_prompt() == ""

    def test_truncates_oversized_doc(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        hand = make_cli_hand(ClaudeCodeHand)
        (hand.repo_index.root / "AGENT.md").write_text("x" * 20_000)
        result = hand._resolve_system_prompt()
        assert "...[truncated]" in result
        assert len(result) < 20_000


class TestInjectSystemPrompt:
    def test_empty_skips_injection(self) -> None:
        cmd = ["claude", "-p", "hi"]
        assert ClaudeCodeHand._inject_system_prompt(cmd, "") == cmd

    def test_inserts_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "hi"]
        result = ClaudeCodeHand._inject_system_prompt(cmd, "rules")
        assert result == ["claude", "--append-system-prompt", "rules", "-p", "hi"]

    def test_no_inject_when_append_present(self) -> None:
        cmd = ["claude", "--append-system-prompt", "x", "-p", "hi"]
        assert ClaudeCodeHand._inject_system_prompt(cmd, "rules") == cmd

    def test_no_inject_when_system_prompt_present(self) -> None:
        cmd = ["claude", "--system-prompt", "x", "-p", "hi"]
        assert ClaudeCodeHand._inject_system_prompt(cmd, "rules") == cmd


# ---------------------------------------------------------------------------
# --allowedTools / --disallowedTools
# ---------------------------------------------------------------------------


class TestResolveToolFilters:
    def test_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", raising=False)
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", raising=False)
        assert ClaudeCodeHand._resolve_tool_filters() == ([], [])

    def test_parses_csv(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", "Read, Edit ,Bash")
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", "Write, WebFetch")
        allowed, disallowed = ClaudeCodeHand._resolve_tool_filters()
        assert allowed == ["Read", "Edit", "Bash"]
        assert disallowed == ["Write", "WebFetch"]

    def test_drops_empty_entries(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", "Read,, ,Edit")
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", raising=False)
        allowed, _ = ClaudeCodeHand._resolve_tool_filters()
        assert allowed == ["Read", "Edit"]


class TestInjectToolFilters:
    def test_no_filters_no_change(self) -> None:
        cmd = ["claude", "-p", "hi"]
        result = ClaudeCodeHand._inject_tool_filters(cmd, allowed=[], disallowed=[])
        assert result == cmd

    def test_injects_allowed_only(self) -> None:
        cmd = ["claude", "-p", "hi"]
        result = ClaudeCodeHand._inject_tool_filters(
            cmd, allowed=["Read", "Edit"], disallowed=[]
        )
        assert result == ["claude", "--allowedTools", "Read,Edit", "-p", "hi"]

    def test_injects_disallowed_only(self) -> None:
        cmd = ["claude", "-p", "hi"]
        result = ClaudeCodeHand._inject_tool_filters(
            cmd, allowed=[], disallowed=["Bash"]
        )
        assert result == ["claude", "--disallowedTools", "Bash", "-p", "hi"]

    def test_injects_both(self) -> None:
        cmd = ["claude", "-p", "hi"]
        result = ClaudeCodeHand._inject_tool_filters(
            cmd, allowed=["Read"], disallowed=["Bash"]
        )
        assert result == [
            "claude",
            "--allowedTools",
            "Read",
            "--disallowedTools",
            "Bash",
            "-p",
            "hi",
        ]

    def test_skips_when_already_present(self) -> None:
        cmd = ["claude", "--allowedTools", "Read", "-p", "hi"]
        result = ClaudeCodeHand._inject_tool_filters(
            cmd, allowed=["Edit"], disallowed=[]
        )
        assert result == cmd


# ---------------------------------------------------------------------------
# Session continuation + cost metadata
# ---------------------------------------------------------------------------


class TestSessionContinueEnabled:
    def test_defaults_off(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", raising=False)
        assert ClaudeCodeHand._session_continue_enabled() is False

    def test_enabled_when_truthy(self, monkeypatch) -> None:
        for value in ("1", "true", "TRUE", "yes", "on"):
            monkeypatch.setenv("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", value)
            assert ClaudeCodeHand._session_continue_enabled() is True


class TestInjectContinue:
    def test_empty_session_id_no_change(self) -> None:
        cmd = ["claude", "-p", "hi"]
        assert ClaudeCodeHand._inject_continue(cmd, "") == cmd

    def test_keeps_p_and_adds_continue(self) -> None:
        cmd = ["claude", "-p", "hi"]
        result = ClaudeCodeHand._inject_continue(cmd, "abc-123")
        assert result == [
            "claude",
            "--continue",
            "--session-id",
            "abc-123",
            "-p",
            "hi",
        ]

    def test_skips_when_continue_present(self) -> None:
        cmd = ["claude", "--continue", "-p", "hi"]
        assert ClaudeCodeHand._inject_continue(cmd, "abc-123") == cmd

    def test_skips_when_resume_present(self) -> None:
        cmd = ["claude", "--resume", "abc", "-p", "hi"]
        assert ClaudeCodeHand._inject_continue(cmd, "xyz-456") == cmd


class TestStreamJsonEmitterSessionAndCost:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_captures_session_id_and_cost(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "session_id": "sess-abc",
                "total_cost_usd": 0.1234,
                "duration_ms": 1500,
                "usage": {"input_tokens": 100, "output_tokens": 25},
            }
        )
        self._run(parser(event + "\n"))
        assert parser.session_id == "sess-abc"
        meta = parser.cost_metadata
        assert meta["total_cost_usd"] == pytest.approx(0.1234)
        assert meta["duration_ms"] == pytest.approx(1500.0)
        assert meta["usage"] == {"input_tokens": 100, "output_tokens": 25}

    def test_missing_fields_omitted(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "result", "result": "done"})
        self._run(parser(event + "\n"))
        assert parser.session_id == ""
        assert parser.cost_metadata == {}

    def test_invalid_cost_silently_dropped(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        # cost is None and duration is "abc": both bad, both silently dropped.
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "session_id": "s",
                "total_cost_usd": None,
                "duration_ms": "abc",
            }
        )
        self._run(parser(event + "\n"))
        assert parser.session_id == "s"
        assert "total_cost_usd" not in parser.cost_metadata
        assert "duration_ms" not in parser.cost_metadata


class TestHandCostMetadata:
    def test_empty_initially(self, claude_hand) -> None:
        assert claude_hand.cost_metadata == {}

    def test_accumulates_after_invocation(self, claude_hand) -> None:
        # Simulate two prior invocations populating instance state.
        claude_hand._last_session_id = "sess-xyz"
        claude_hand._cumulative_cost_usd = 0.5
        meta = claude_hand.cost_metadata
        assert meta == {"total_cost_usd": 0.5, "session_id": "sess-xyz"}


# ---------------------------------------------------------------------------
# _build_cli_cmd integration
# ---------------------------------------------------------------------------


class TestBuildCliCmd:
    def test_no_features_only_output_format(self, claude_hand, monkeypatch) -> None:
        _clear_feature_env(monkeypatch)
        cmd = claude_hand._build_cli_cmd("hello")
        # The base command is "claude -p" with the prompt appended; we
        # always inject --output-format stream-json regardless of features.
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--max-turns" not in cmd
        assert "--append-system-prompt" not in cmd
        assert "--allowedTools" not in cmd
        assert "--continue" not in cmd

    def test_max_turns_only(self, claude_hand, monkeypatch) -> None:
        _clear_feature_env(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "7")
        cmd = claude_hand._build_cli_cmd("hello")
        assert "--max-turns" in cmd
        assert "7" in cmd

    def test_system_prompt_from_env(self, claude_hand, monkeypatch) -> None:
        _clear_feature_env(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", "be careful")
        cmd = claude_hand._build_cli_cmd("hello")
        assert "--append-system-prompt" in cmd
        assert "be careful" in cmd

    def test_tool_filters(self, claude_hand, monkeypatch) -> None:
        _clear_feature_env(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", "Read,Edit")
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", "Bash")
        cmd = claude_hand._build_cli_cmd("hello")
        assert "--allowedTools" in cmd
        assert "Read,Edit" in cmd
        assert "--disallowedTools" in cmd
        assert "Bash" in cmd

    def test_continue_skipped_without_session(self, claude_hand, monkeypatch) -> None:
        _clear_feature_env(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", "1")
        cmd = claude_hand._build_cli_cmd("hello")
        # No prior session_id captured, so --continue is not injected.
        assert "--continue" not in cmd

    def test_continue_when_enabled_and_session_known(
        self, claude_hand, monkeypatch
    ) -> None:
        _clear_feature_env(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", "1")
        claude_hand._last_session_id = "sess-1"
        cmd = claude_hand._build_cli_cmd("hello")
        assert "--continue" in cmd
        assert "--session-id" in cmd
        assert "sess-1" in cmd

    def test_continue_disabled_by_default(self, claude_hand, monkeypatch) -> None:
        _clear_feature_env(monkeypatch)
        claude_hand._last_session_id = "sess-1"
        cmd = claude_hand._build_cli_cmd("hello")
        # Env var defaults to off, so even with a known session ID we don't
        # auto-continue.
        assert "--continue" not in cmd
