from __future__ import annotations

from src.results_pipeline.cli import main


def test_cli_version_returns_zero() -> None:
    rc = main(["--version"])
    assert rc == 0


def test_cli_list_stages_returns_zero() -> None:
    rc = main(["list-stages"])
    assert rc == 0
