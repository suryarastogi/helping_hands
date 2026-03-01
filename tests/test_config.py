"""Tests for helping_hands.lib.config."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

import helping_hands.lib.config as config_module
from helping_hands.lib.config import Config


class TestConfigDefaults:
    def test_defaults(self) -> None:
        config = Config()
        assert config.repo == ""
        assert config.model == "default"
        assert config.verbose is False
        assert config.enable_execution is False
        assert config.enable_web is False
        assert config.use_native_cli_auth is False
        assert config.enabled_skills == ()

    def test_from_env_picks_up_env_var(self, monkeypatch: object) -> None:
        os.environ["HELPING_HANDS_MODEL"] = "gpt-test"
        try:
            config = Config.from_env()
            assert config.model == "gpt-test"
        finally:
            del os.environ["HELPING_HANDS_MODEL"]

    def test_overrides_beat_env(self) -> None:
        os.environ["HELPING_HANDS_MODEL"] = "from-env"
        try:
            config = Config.from_env(overrides={"model": "from-cli"})
            assert config.model == "from-cli"
        finally:
            del os.environ["HELPING_HANDS_MODEL"]

    def test_from_env_picks_up_tool_flags(self) -> None:
        os.environ["HELPING_HANDS_ENABLE_EXECUTION"] = "1"
        os.environ["HELPING_HANDS_ENABLE_WEB"] = "true"
        os.environ["HELPING_HANDS_USE_NATIVE_CLI_AUTH"] = "yes"
        os.environ["HELPING_HANDS_SKILLS"] = "execution, web"
        try:
            config = Config.from_env()
            assert config.enable_execution is True
            assert config.enable_web is True
            assert config.use_native_cli_auth is True
            assert config.enabled_skills == ("execution", "web")
        finally:
            del os.environ["HELPING_HANDS_ENABLE_EXECUTION"]
            del os.environ["HELPING_HANDS_ENABLE_WEB"]
            del os.environ["HELPING_HANDS_USE_NATIVE_CLI_AUTH"]
            del os.environ["HELPING_HANDS_SKILLS"]

    def test_from_env_loads_dotenv(self, tmp_path: Path, monkeypatch: object) -> None:
        loaded_paths: list[Path] = []
        env_file = tmp_path / ".env"
        env_file.write_text("HELPING_HANDS_MODEL=from-dotenv\n")

        def fake_load_dotenv(path: Path, override: bool = False) -> bool:
            loaded_paths.append(path)
            if path == env_file:
                os.environ["HELPING_HANDS_MODEL"] = "from-dotenv"
            return True

        if "HELPING_HANDS_MODEL" in os.environ:
            del os.environ["HELPING_HANDS_MODEL"]
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)

        try:
            config = Config.from_env()
            assert config.model == "from-dotenv"
            assert env_file in loaded_paths
        finally:
            if "HELPING_HANDS_MODEL" in os.environ:
                del os.environ["HELPING_HANDS_MODEL"]


class TestConfigSkillsValidation:
    def test_valid_skills_no_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            Config(enabled_skills=("execution", "web"))
        assert "Unrecognized skill" not in caplog.text

    def test_empty_skills_no_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            Config(enabled_skills=())
        assert "Unrecognized skill" not in caplog.text

    def test_unknown_skill_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            Config(enabled_skills=("execution", "nonexistent"))
        assert "Unrecognized skill(s): nonexistent" in caplog.text
        assert "available:" in caplog.text

    def test_multiple_unknown_skills_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            Config(enabled_skills=("bad1", "bad2"))
        assert "bad1" in caplog.text
        assert "bad2" in caplog.text
