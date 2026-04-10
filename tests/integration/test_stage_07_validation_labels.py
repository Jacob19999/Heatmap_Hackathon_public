"""Validation: All Stage 07 outputs are explicitly scenario-labeled."""
from __future__ import annotations

from pathlib import Path

import json
import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_07_air_sensitivity import run


def _upstream(tmp_path: Path) -> None:
    (tmp_path / "data" / "processed").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "tract_geoid": ["27123000100"],
        "state_fips": ["27"],
        "travel_minutes": [50.0],
        "total_pop": [4000],
    }).to_parquet(tmp_path / "data" / "processed" / "ground_access_burden.parquet", index=False)


def test_stage_07_all_outputs_scenario_labeled(tmp_path: Path) -> None:
    _upstream(tmp_path)
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
        },
        source_paths=[],
    )
    result = run(cfg)
    assert "ground_plus_air" in result["dataset"]
    assert "ground_plus_air" in result["finding"]
    finding_path = Path(result["finding"])
    finding = json.loads(finding_path.read_text(encoding="utf-8"))
    assert finding.get("scenario_id") == "ground_plus_air"
    df = pd.read_parquet(tmp_path / "data" / "processed" / "air_sensitivity_ground_plus_air.parquet")
    assert "scenario" in df.columns and (df["scenario"] == "ground_plus_air").all()
