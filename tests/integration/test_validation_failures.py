from __future__ import annotations

from src.results_pipeline.cli import main
from src.results_pipeline.orchestrator import run_pipeline, validate_pipeline
from src.results_pipeline.settings import RuntimeConfig


def test_validate_pipeline_fails_when_dependencies_missing() -> None:
    cfg = RuntimeConfig(raw={"profile": "stage", "stages": ["03"], "scenario": "ground_only"}, source_paths=[])
    result = validate_pipeline(cfg)
    assert result["ok"] is False
    assert result["errors"]


def test_run_pipeline_fails_when_dependencies_missing() -> None:
    cfg = RuntimeConfig(raw={"profile": "stage", "stages": ["03"], "scenario": "ground_only"}, source_paths=[])
    result = run_pipeline(cfg)
    assert result["ok"] is False


def test_cli_validate_returns_nonzero_on_validation_failure(tmp_path) -> None:
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("profile: stage\nstages: ['03']\nscenario: ground_only\n", encoding="utf-8")
    rc = main(["validate", "--config", str(cfg)])
    assert rc == 3
