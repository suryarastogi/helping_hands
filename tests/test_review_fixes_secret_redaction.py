"""Tests for ``_redact_secrets`` used when verbosely emitting CLI commands.

The verbose ``cmd:`` line can embed the substituted user prompt, which may
contain secrets. ``_redact_secrets`` masks common token formats before the
command string is emitted.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _redact_secrets


@pytest.mark.parametrize(
    "secret",
    [
        "ghp_0123456789abcdefghijklmnopqrstuvwxyz",
        "gho_0123456789abcdefghijklmnopqrstuvwxyz",
        "ghu_0123456789abcdefghijklmnopqrstuvwxyz",
        "ghs_0123456789abcdefghijklmnopqrstuvwxyz",
        "ghr_0123456789abcdefghijklmnopqrstuvwxyz",
    ],
)
def test_redacts_github_classic_tokens(secret: str) -> None:
    out = _redact_secrets(f"token is {secret} ok")
    assert secret not in out
    assert "***" in out


def test_redacts_github_fine_grained_pat() -> None:
    secret = "github_pat_11ABCDEFG0abcdefghijkl_mnopqrstuvwxyz0123456789ABCDEF"
    out = _redact_secrets(f"pat={secret}")
    assert secret not in out
    assert "***" in out


def test_redacts_openai_key() -> None:
    secret = "sk-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH"
    out = _redact_secrets(f"OPENAI is {secret}")
    assert secret not in out
    assert "***" in out


def test_redacts_anthropic_key() -> None:
    secret = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789ABCDEF"
    out = _redact_secrets(f"key {secret} end")
    assert secret not in out
    # The whole key including the sk-ant- prefix must be gone.
    assert "sk-ant" not in out
    assert "***" in out


def test_redacts_aws_access_key_id() -> None:
    secret = "AKIAIOSFODNN7EXAMPLE"
    out = _redact_secrets(f"aws {secret} here")
    assert secret not in out
    assert "***" in out


@pytest.mark.parametrize(
    "pair",
    [
        "API_KEY=supersecretvalue123",
        "GITHUB_TOKEN=tok_abcdef123456",
        "MY_SECRET=hunter2hunter2",
        "DB_PASSWORD=p@ssw0rd!value",
    ],
)
def test_redacts_key_value_pairs(pair: str) -> None:
    name, value = pair.split("=", 1)
    out = _redact_secrets(f"env {pair} tail")
    assert value not in out
    # The name is preserved so the message stays useful.
    assert name in out
    assert f"{name}=***" in out


def test_key_value_pair_is_case_insensitive() -> None:
    out = _redact_secrets("myApiKey=abc123def456")
    assert "abc123def456" not in out
    assert "***" in out


def test_leaves_non_secret_text_untouched() -> None:
    text = "run tool foo --verbose --path /repo/src file.py"
    assert _redact_secrets(text) == text


def test_redacts_multiple_secrets_in_one_string() -> None:
    a = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
    b = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789ABCDEF"
    out = _redact_secrets(f"first {a} then TOKEN=zzz9998887 then {b}")
    assert a not in out
    assert b not in out
    assert "zzz9998887" not in out
