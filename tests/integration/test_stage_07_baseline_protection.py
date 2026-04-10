"""Validation: Stage 07 does not modify baseline ground-only artifacts."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_07_air_sensitivity import run


def _upstream(tmp_path: Path) -> None:
    (tmp_path / "data" / "processed").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "tract_geoid": ["27123000100"],
        "state_fips": ["27"],
        "travel_minutes": [50.0],
    }).to_parquet(tmp_path / "data" / "processed" / "ground_access_burden.parquet", index=False)


def test_stage_07_does_not_modify_ground_only_artifacts(tmp_path: Path) -> None:
    _upstream(tmp_path)
    baseline_path = tmp_path / "data" / "processed" / "ground_access_burden.parquet"
    before = baseline_path.read_bytes()
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
    after = baseline_path.read_bytes()
    assert before == after
