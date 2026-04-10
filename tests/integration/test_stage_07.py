"""Integration test for Stage 07 using ground_plus_air scenario config."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_07_air_sensitivity import run


def _ground_access_artifact(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    access = pd.DataFrame({
        "tract_geoid": ["27123000100", "27123000200", "55025000100"],
        "state_fips": ["27", "27", "55"],
        "county_fips": ["27123", "27123", "55025"],
        "travel_minutes": [45.0, 90.0, 120.0],
        "total_pop": [4000, 5000, 6000],
    })
    access.to_parquet(processed / "ground_access_burden.parquet", index=False)


def test_stage_07_runs_with_ground_plus_air_scenario(tmp_path: Path) -> None:
    _ground_access_artifact(tmp_path)
    cfg = RuntimeConfig(
        raw={
            "profile": "full",
            "scenario": "ground_plus_air",
            "data": {
                "ground_access_burden_path": str(tmp_path / "data" / "processed" / "ground_access_burden.parquet"),
                "processed_dir": str(tmp_path / "data" / "processed"),
            },
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
            "air_assumptions": {"air_cap_minutes": 60, "air_speed_factor": 0.4},
        },
        source_paths=[],
    )
    result = run(cfg)
    assert result["ok"] is True
    assert result.get("scenario_id") == "ground_plus_air"
    assert "ground_plus_air" in result["dataset"]
    assert Path(result["finding"]).exists()


def test_stage_07_outputs_are_scenario_labeled(tmp_path: Path) -> None:
    _ground_access_artifact(tmp_path)
    cfg = RuntimeConfig(
        raw={
            "profile": "full",
            "scenario": "ground_plus_air",
            "data": {
                "ground_access_burden_path": str(tmp_path / "data" / "processed" / "ground_access_burden.parquet"),
                "processed_dir": str(tmp_path / "data" / "processed"),
            },
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
            "air_assumptions": {"air_cap_minutes": 60, "air_speed_factor": 0.4},
        },
        source_paths=[],
    )
    run(cfg)
    df = pd.read_parquet(tmp_path / "data" / "processed" / "air_sensitivity_ground_plus_air.parquet")
    assert "scenario" in df.columns
    assert (df["scenario"] == "ground_plus_air").all()


def test_stage_07_does_not_overwrite_ground_only_baseline(tmp_path: Path) -> None:
    _ground_access_artifact(tmp_path)
    baseline_path = tmp_path / "data" / "processed" / "ground_access_burden.parquet"
    baseline_before = baseline_path.read_bytes()
    cfg = RuntimeConfig(
        raw={
            "profile": "full",
            "scenario": "ground_plus_air",
            "data": {
                "ground_access_burden_path": str(baseline_path),
                "processed_dir": str(tmp_path / "data" / "processed"),
            },
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
        },
        source_paths=[],
    )
    run(cfg)
    baseline_after = baseline_path.read_bytes()
    assert baseline_before == baseline_after
