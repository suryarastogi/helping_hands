"""Tests for v343: cli/main.py max_iterations=None default branch coverage.

The ``--max-iterations`` argparse default was ``6``, making the
``if args.max_iterations is not None:`` guard on line 336 always True.
After changing the default to ``None``, both branches are reachable:

* **True path** — ``--max-iterations 3`` triggers validation.
* **False path** — omitting the flag leaves ``args.max_iterations`` as
  ``None``, skipping validation and letting the hand use its own default.
"""

from __future__ import annotations

from pathlib import Path

from helping_hands.cli.main import build_parser, main


class TestMaxIterationsDefaultIsNone:
    """Verify argparse default for --max-iterations is None."""

    def test_default_is_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["some/repo"])
        assert args.max_iterations is None

    def test_explicit_value_is_int(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["some/repo", "--max-iterations", "3"])
        assert args.max_iterations == 3


class TestMaxIterationsNoneSkipsValidation:
    """Verify main() without --max-iterations reaches the hand path."""

    def test_no_max_iterations_runs_basic_mode(
        self, tmp_path: Path, capsys: object
    ) -> None:
        """Omitting --max-iterations should not trigger validation or crash."""
        (tmp_path / "hello.py").write_text("")
        # Without --backend, main() enters the basic interactive path and
        # prints "Ready …" — this exercises the False branch at line 336.
        main([str(tmp_path)])

    def test_explicit_max_iterations_still_validates(self) -> None:
        """Positive --max-iterations passes validation (True branch)."""
        import pytest

        # Zero triggers require_positive_int → SystemExit, proving validation
        # runs when max_iterations is not None.
        with pytest.raises(SystemExit):
            main(["/tmp/repo", "--max-iterations", "0", "--prompt", "test"])
