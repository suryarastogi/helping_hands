"""Tests for helping_hands.lib.config."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import helping_hands.lib.config as config_module
from helping_hands.lib.config import Config


class TestConfigDefaults:
    def test_defaults(self) -> None:
        config = Config()
        assert config.repo == ""
        assert config.model == "default"
        assert config.verbose is True
        assert config.enable_execution is False
        assert config.enable_web is False
        assert config.use_native_cli_auth is False
        assert config.enabled_tools == ()
        assert config.enabled_skills == ()

    def test_frozen_immutability(self) -> None:
        """Config is a frozen dataclass; attribute assignment raises."""
        config = Config()
        with pytest.raises(FrozenInstanceError):
            config.model = "changed"  # type: ignore[misc]

    def test_from_env_picks_up_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "gpt-test")
        config = Config.from_env()
        assert config.model == "gpt-test"

    def test_overrides_beat_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "from-env")
        config = Config.from_env(overrides={"model": "from-cli"})
        assert config.model == "from-cli"

    def test_from_env_picks_up_tool_flags(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_ENABLE_EXECUTION", "1")
        monkeypatch.setenv("HELPING_HANDS_ENABLE_WEB", "true")
        monkeypatch.setenv("HELPING_HANDS_USE_NATIVE_CLI_AUTH", "yes")
        monkeypatch.setenv("HELPING_HANDS_SKILLS", "execution, web")
        config = Config.from_env()
        assert config.enable_execution is True
        assert config.enable_web is True
        assert config.use_native_cli_auth is True
        assert config.enabled_skills == ("execution", "web")

    def test_from_env_empty_model_env_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "")
        config = Config.from_env()
        assert config.model == "default"

    def test_from_env_boolean_tools_flag_normalizes_to_empty_tuple(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When HELPING_HANDS_TOOLS is unset, enabled_tools remains empty."""
        monkeypatch.delenv("HELPING_HANDS_TOOLS", raising=False)
        config = Config.from_env()
        assert config.enabled_tools == ()

    def test_from_env_comma_separated_tools_parsed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_TOOLS", "python.run_code, bash.run_script")
        config = Config.from_env()
        assert len(config.enabled_tools) == 2
        assert any("python" in t for t in config.enabled_tools)
        assert any("bash" in t for t in config.enabled_tools)

    def test_override_none_does_not_clobber_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "from-env")
        config = Config.from_env(overrides={"model": None})
        assert config.model == "from-env"

    def test_from_env_loads_dotenv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        loaded_paths: list[Path] = []
        env_file = tmp_path / ".env"
        env_file.write_text("HELPING_HANDS_MODEL=from-dotenv\n")

        def fake_load_dotenv(path: Path, override: bool = False) -> bool:
            loaded_paths.append(path)
            if path == env_file:
                monkeypatch.setenv("HELPING_HANDS_MODEL", "from-dotenv")
            return True

        monkeypatch.delenv("HELPING_HANDS_MODEL", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)

        config = Config.from_env()
        assert config.model == "from-dotenv"
        assert env_file in loaded_paths


class TestLoadEnvFilesNoDotenv:
    def test_returns_early_when_load_dotenv_is_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When python-dotenv is not installed, _load_env_files exits early."""
        monkeypatch.setattr(config_module, "load_dotenv", None)
        config_module._load_env_files(repo="/some/path")


class TestBoolToolAndSkillOverrides:
    def test_bool_tools_override_normalizes_to_empty_tuple(self) -> None:
        """If overrides pass enabled_tools=True (a bool), it normalizes to ()."""
        config = Config.from_env(overrides={"enabled_tools": True})
        assert config.enabled_tools == ()

    def test_bool_skills_override_normalizes_to_empty_tuple(self) -> None:
        """If overrides pass enabled_skills=True (a bool), it normalizes to ()."""
        config = Config.from_env(overrides={"enabled_skills": True})
        assert config.enabled_skills == ()


class TestFromEnvRepoDotenv:
    def test_repo_override_triggers_dotenv_from_repo_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When repo override points at a dir, dotenv loads from that dir too."""
        loaded_paths: list[Path] = []

        def fake_load_dotenv(path: Path, override: bool = False) -> bool:
            loaded_paths.append(path)
            return True

        monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)
        monkeypatch.delenv("HELPING_HANDS_MODEL", raising=False)

        config = Config.from_env(overrides={"repo": str(tmp_path)})
        repo_env_file = tmp_path / ".env"
        assert repo_env_file in loaded_paths
        assert config.repo == str(tmp_path)


class TestFromEnvVerbose:
    def test_verbose_truthy_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for val in ("1", "true", "yes", "True", "YES"):
            monkeypatch.setenv("HELPING_HANDS_VERBOSE", val)
            config = Config.from_env()
            assert config.verbose is True, f"Expected verbose=True for {val!r}"

    def test_verbose_falsy_env_keeps_default_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falsy env values produce verbose=False which is filtered by the
        truthy merge, so the default (True) is preserved."""
        for val in ("0", "false", "no", ""):
            monkeypatch.setenv("HELPING_HANDS_VERBOSE", val)
            config = Config.from_env()
            assert config.verbose is True, f"Expected default verbose=True for {val!r}"

    def test_verbose_override_false(self) -> None:
        """Explicit override can set verbose=False."""
        config = Config.from_env(overrides={"verbose": False})
        assert config.verbose is False

    def test_verbose_override_true(self) -> None:
        """Explicit override can set verbose=True."""
        config = Config.from_env(overrides={"verbose": True})
        assert config.verbose is True


class TestLoadEnvFilesNonDirRepo:
    def test_non_directory_repo_skips_repo_dotenv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When repo path is not a directory, only cwd dotenv is loaded."""
        loaded_paths: list[Path] = []

        def fake_load_dotenv(path: Path, override: bool = False) -> bool:
            loaded_paths.append(path)
            return True

        monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)
        monkeypatch.chdir(tmp_path)

        fake_repo = str(tmp_path / "nonexistent")
        config_module._load_env_files(repo=fake_repo)

        # Only cwd .env should be loaded, not the repo .env
        assert len(loaded_paths) == 1
        assert loaded_paths[0] == tmp_path / ".env"

    def test_none_repo_skips_repo_dotenv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When repo is None, only cwd dotenv is loaded."""
        loaded_paths: list[Path] = []

        def fake_load_dotenv(path: Path, override: bool = False) -> bool:
            loaded_paths.append(path)
            return True

        monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)
        monkeypatch.chdir(tmp_path)

        config_module._load_env_files(repo=None)
        assert len(loaded_paths) == 1


class TestLoadEnvFilesTildeExpansion:
    def test_tilde_path_is_expanded_before_is_dir_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When repo contains ~, expanduser() resolves it before is_dir()."""
        loaded_paths: list[Path] = []

        def fake_load_dotenv(path: Path, override: bool = False) -> bool:
            loaded_paths.append(path)
            return True

        monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)
        monkeypatch.chdir(tmp_path)

        # Monkeypatch expanduser so ~ maps to tmp_path
        real_dir = tmp_path / "myrepo"
        real_dir.mkdir()
        monkeypatch.setattr(Path, "expanduser", lambda self: real_dir)

        config_module._load_env_files(repo="~/myrepo")

        # Both cwd .env and expanded repo .env should be loaded
        assert len(loaded_paths) == 2
        assert loaded_paths[1] == real_dir / ".env"


class TestConfigPathField:
    def test_config_path_default_is_none(self) -> None:
        config = Config()
        assert config.config_path is None

    def test_config_path_can_be_set(self, tmp_path: Path) -> None:
        config = Config(config_path=tmp_path / "config.toml")
        assert config.config_path == tmp_path / "config.toml"

    def test_config_path_is_frozen(self, tmp_path: Path) -> None:
        config = Config(config_path=tmp_path / "config.toml")
        with pytest.raises(FrozenInstanceError):
            config.config_path = None  # type: ignore[misc]


class TestFromEnvToolsAndSkillsStringOverrides:
    def test_string_tools_override_parsed(self) -> None:
        """String overrides for enabled_tools are normalized."""
        config = Config.from_env(
            overrides={"enabled_tools": "python.run_code, bash.run_script"}
        )
        assert len(config.enabled_tools) == 2

    def test_string_skills_override_parsed(self) -> None:
        """String overrides for enabled_skills are normalized."""
        config = Config.from_env(overrides={"enabled_skills": "execution, web"})
        assert config.enabled_skills == ("execution", "web")

    def test_tuple_tools_override_normalized(self) -> None:
        """Tuple overrides for enabled_tools are normalized (underscores to dashes)."""
        config = Config.from_env(overrides={"enabled_tools": ("python.run_code",)})
        assert config.enabled_tools == ("python.run-code",)


class TestFromEnvPrecedence:
    def test_env_model_used_when_no_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "env-model")
        config = Config.from_env()
        assert config.model == "env-model"

    def test_override_beats_env_for_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """String overrides win over env vars."""
        monkeypatch.setenv("HELPING_HANDS_MODEL", "env-model")
        config = Config.from_env(overrides={"model": "override-model"})
        assert config.model == "override-model"

    def test_false_override_beats_truthy_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """False override for a boolean field overrides a truthy env var."""
        monkeypatch.setenv("HELPING_HANDS_ENABLE_EXECUTION", "1")
        config = Config.from_env(overrides={"enable_execution": False})
        assert config.enable_execution is False

    def test_no_overrides_no_env_uses_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no env vars and no overrides, defaults are used."""
        monkeypatch.delenv("HELPING_HANDS_MODEL", raising=False)
        monkeypatch.delenv("HELPING_HANDS_VERBOSE", raising=False)
        monkeypatch.delenv("HELPING_HANDS_ENABLE_EXECUTION", raising=False)
        monkeypatch.delenv("HELPING_HANDS_ENABLE_WEB", raising=False)
        monkeypatch.delenv("HELPING_HANDS_USE_NATIVE_CLI_AUTH", raising=False)
        monkeypatch.delenv("HELPING_HANDS_TOOLS", raising=False)
        monkeypatch.delenv("HELPING_HANDS_SKILLS", raising=False)
        config = Config.from_env()
        assert config.model == "default"
        assert config.verbose is True
        assert config.enable_execution is False
        assert config.enabled_tools == ()

    def test_empty_overrides_dict_treated_as_no_overrides(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "env-model")
        config = Config.from_env(overrides={})
        assert config.model == "env-model"

    def test_repo_override_sets_repo_field(self) -> None:
        config = Config.from_env(overrides={"repo": "/tmp/myrepo"})
        assert config.repo == "/tmp/myrepo"
