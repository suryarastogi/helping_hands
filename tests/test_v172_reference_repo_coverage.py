"""Guard the error-handling paths in reference-repo cloning and script execution.

These tests protect four behavioural invariants that are easy to break during
refactoring: (1) invalid owner/repo specs are skipped with a warning rather than
raising unhandled exceptions; (2) git-clone timeouts are caught and skipped with
a warning so one slow network call cannot abort the whole run; (3) valid specs that
follow an invalid one still get cloned; (4) _run_bash_script rejects calls where
both script_path and code are None. If these paths regress, users will see cryptic
tracebacks instead of actionable warnings when reference repos are misconfigured,
and scripts will silently do nothing when called incorrectly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.cli.main import _clone_reference_repos
from helping_hands.lib.config import Config
from helping_hands.lib.meta.tools.registry import _run_bash_script
from helping_hands.lib.repo import RepoIndex


class TestCloneReferenceReposInvalidSpec:
    """Lines 440-442: invalid repo spec is skipped with a warning."""

    def test_invalid_spec_skipped_with_warning(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_index = RepoIndex(root=tmp_path, files=[])
        _clone_reference_repos(("bad-no-slash",), repo_index)
        captured = capsys.readouterr()
        assert "Warning: skipping invalid reference repo" in captured.out
        assert "bad-no-slash" in captured.out
        assert len(repo_index.reference_repos) == 0

    def test_empty_spec_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_index = RepoIndex(root=tmp_path, files=[])
        _clone_reference_repos(("",), repo_index)
        captured = capsys.readouterr()
        assert "Warning: skipping invalid reference repo" in captured.out
        assert len(repo_index.reference_repos) == 0

    def test_valid_specs_still_processed_after_invalid(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An invalid spec does not prevent later valid specs from cloning."""
        dest = tmp_path / "cloned" / "repo"
        dest.mkdir(parents=True)
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        with (
            patch("helping_hands.cli.main.subprocess.run", return_value=mock_result),
            patch(
                "helping_hands.cli.main.mkdtemp", return_value=str(tmp_path / "cloned")
            ),
            patch("helping_hands.cli.main.atexit.register"),
        ):
            repo_index = RepoIndex(root=tmp_path, files=[])
            _clone_reference_repos(
                ("bad", "owner/repo"), repo_index, github_token="tok"
            )
        captured = capsys.readouterr()
        assert "Warning: skipping invalid reference repo" in captured.out
        assert len(repo_index.reference_repos) == 1


class TestCloneReferenceReposTimeout:
    """Lines 466-468: git clone timeout is skipped with a warning."""

    @patch("helping_hands.cli.main.atexit.register")
    @patch("helping_hands.cli.main.mkdtemp")
    @patch("helping_hands.cli.main.subprocess.run")
    def test_timeout_skipped_with_warning(
        self,
        mock_run: MagicMock,
        mock_mkdtemp: MagicMock,
        _mock_atexit: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_mkdtemp.return_value = str(tmp_path / "ref_dir")
        (tmp_path / "ref_dir").mkdir()
        mock_run.side_effect = TimeoutExpired(cmd="git clone", timeout=120)
        repo_index = RepoIndex(root=tmp_path, files=[])
        _clone_reference_repos(("owner/repo",), repo_index)
        captured = capsys.readouterr()
        assert "Warning:" in captured.out
        assert "timed out" in captured.out
        assert "owner/repo" in captured.out
        assert len(repo_index.reference_repos) == 0

    @patch("helping_hands.cli.main.atexit.register")
    @patch("helping_hands.cli.main.mkdtemp")
    @patch("helping_hands.cli.main.subprocess.run")
    def test_timeout_does_not_stop_later_repos(
        self,
        mock_run: MagicMock,
        mock_mkdtemp: MagicMock,
        _mock_atexit: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Timeout on first repo does not prevent second from cloning."""
        ref1 = tmp_path / "ref1"
        ref1.mkdir()
        ref2 = tmp_path / "ref2"
        ref2.mkdir()
        (ref2 / "repo").mkdir()
        mock_mkdtemp.side_effect = [str(ref1), str(ref2)]
        mock_run.side_effect = [
            TimeoutExpired(cmd="git clone", timeout=120),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        repo_index = RepoIndex(root=tmp_path, files=[])
        _clone_reference_repos(("owner/repo1", "owner/repo2"), repo_index)
        captured = capsys.readouterr()
        assert "timed out" in captured.out
        assert len(repo_index.reference_repos) == 1


class TestCloneReferenceReposSuccess:
    """Lines 473-475: successful clone appends to repo_index."""

    @patch("helping_hands.cli.main.atexit.register")
    @patch("helping_hands.cli.main.mkdtemp")
    @patch("helping_hands.cli.main.subprocess.run")
    def test_successful_clone_appends(
        self,
        mock_run: MagicMock,
        mock_mkdtemp: MagicMock,
        _mock_atexit: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dest_root = tmp_path / "ref"
        dest_root.mkdir()
        (dest_root / "repo").mkdir()
        mock_mkdtemp.return_value = str(dest_root)
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        repo_index = RepoIndex(root=tmp_path, files=[])
        _clone_reference_repos(("owner/repo",), repo_index, github_token="tok")
        assert len(repo_index.reference_repos) == 1
        name, path = repo_index.reference_repos[0]
        assert name == "owner/repo"
        assert path == (dest_root / "repo").resolve()
        captured = capsys.readouterr()
        assert "Cloned reference repo owner/repo" in captured.out

    @patch("helping_hands.cli.main.atexit.register")
    @patch("helping_hands.cli.main.mkdtemp")
    @patch("helping_hands.cli.main.subprocess.run")
    def test_clone_failure_skipped_with_warning(
        self,
        mock_run: MagicMock,
        mock_mkdtemp: MagicMock,
        _mock_atexit: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Non-zero returncode skips the repo with a warning."""
        dest_root = tmp_path / "ref"
        dest_root.mkdir()
        mock_mkdtemp.return_value = str(dest_root)
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: repo not found"
        )
        repo_index = RepoIndex(root=tmp_path, files=[])
        _clone_reference_repos(("owner/repo",), repo_index)
        assert len(repo_index.reference_repos) == 0
        captured = capsys.readouterr()
        assert "Warning:" in captured.out
        assert "failed to clone" in captured.out
        assert "owner/repo" in captured.out

    @patch("helping_hands.cli.main.atexit.register")
    @patch("helping_hands.cli.main.mkdtemp")
    @patch("helping_hands.cli.main.subprocess.run")
    def test_multiple_successful_clones(
        self,
        mock_run: MagicMock,
        mock_mkdtemp: MagicMock,
        _mock_atexit: MagicMock,
        tmp_path: Path,
    ) -> None:
        ref1 = tmp_path / "ref1"
        ref1.mkdir()
        (ref1 / "repo").mkdir()
        ref2 = tmp_path / "ref2"
        ref2.mkdir()
        (ref2 / "repo").mkdir()
        mock_mkdtemp.side_effect = [str(ref1), str(ref2)]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        repo_index = RepoIndex(root=tmp_path, files=[])
        _clone_reference_repos(("a/b", "c/d"), repo_index)
        assert len(repo_index.reference_repos) == 2
        assert repo_index.reference_repos[0][0] == "a/b"
        assert repo_index.reference_repos[1][0] == "c/d"


# ---------------------------------------------------------------------------
# Config.from_env reference_repos non-str/non-list/tuple fallback
# ---------------------------------------------------------------------------


class TestConfigReferenceReposTypeFallback:
    """Line 133: non-str/non-list/tuple reference_repos falls back to ()."""

    def test_int_falls_back_to_empty(self) -> None:
        config = Config.from_env(overrides={"reference_repos": 42})
        assert config.reference_repos == ()

    def test_dict_falls_back_to_empty(self) -> None:
        config = Config.from_env(overrides={"reference_repos": {"a": "b"}})
        assert config.reference_repos == ()

    def test_set_falls_back_to_empty(self) -> None:
        config = Config.from_env(overrides={"reference_repos": {1, 2}})
        assert config.reference_repos == ()

    def test_bool_falls_back_to_empty(self) -> None:
        config = Config.from_env(overrides={"reference_repos": True})
        assert config.reference_repos == ()

    def test_none_falls_back_to_default(self) -> None:
        """None is the sentinel for 'no override'; should use class default."""
        config = Config.from_env(overrides={"reference_repos": None})
        assert config.reference_repos == ()


# ---------------------------------------------------------------------------
# Hand._build_reference_repos_prompt_section PermissionError
# ---------------------------------------------------------------------------


class TestBuildReferenceReposPromptSectionPermissionError:
    """Lines 153-154: PermissionError during rglob shows '(permission denied)'."""

    def test_permission_error_shows_fallback_message(self, tmp_path: Path) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        repo_index = RepoIndex(root=tmp_path, files=["main.py"])
        ref_path = tmp_path / "ref_repo"
        ref_path.mkdir()
        repo_index.reference_repos.append(("owner/ref", ref_path))

        # Create a concrete subclass to test the method
        class _ConcreteHand(Hand):
            def run(self, prompt: str):  # type: ignore[override]
                pass

            async def stream(self, prompt: str):  # type: ignore[override]
                yield ""  # pragma: no cover

        hand = _ConcreteHand(
            config=Config(repo=str(tmp_path), model="test"),
            repo_index=repo_index,
        )

        with patch.object(Path, "rglob", side_effect=PermissionError("denied")):
            section = hand._build_reference_repos_prompt_section()

        assert "(permission denied)" in section
        assert "owner/ref" in section

    def test_normal_listing_works(self, tmp_path: Path) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        repo_index = RepoIndex(root=tmp_path, files=["main.py"])
        ref_path = tmp_path / "ref_repo"
        ref_path.mkdir()
        (ref_path / "README.md").write_text("hello")
        repo_index.reference_repos.append(("owner/ref", ref_path))

        class _ConcreteHand(Hand):
            def run(self, prompt: str):  # type: ignore[override]
                pass

            async def stream(self, prompt: str):  # type: ignore[override]
                yield ""  # pragma: no cover

        hand = _ConcreteHand(
            config=Config(repo=str(tmp_path), model="test"),
            repo_index=repo_index,
        )
        section = hand._build_reference_repos_prompt_section()
        assert "owner/ref" in section
        assert "README.md" in section
        assert "(permission denied)" not in section


# ---------------------------------------------------------------------------
# _run_bash_script: both-None validation
# ---------------------------------------------------------------------------


class TestRunBashScriptBothNoneValidation:
    """Line 228: neither script_path nor inline_script raises ValueError."""

    def test_neither_provided_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="provide exactly one"):
            _run_bash_script(tmp_path, {})

    def test_both_provided_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="provide exactly one"):
            _run_bash_script(
                tmp_path, {"script_path": "run.sh", "inline_script": "echo hi"}
            )

    def test_only_none_values_raises(self, tmp_path: Path) -> None:
        """Explicit None for both should also raise."""
        with pytest.raises(ValueError, match="provide exactly one"):
            _run_bash_script(tmp_path, {"script_path": None, "inline_script": None})
