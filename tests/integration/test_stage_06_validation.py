"""Validation: Stage 06 outputs are clearly structural, not real-time."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_06_structural_capacity import run


def _upstream(tmp_path: Path) -> None:
    (tmp_path / "data" / "processed").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "STATE": ["MN"],
        "county_fips": ["27123"],
        "BURN_BEDS": [10],
    }).to_parquet(tmp_path / "data" / "processed" / "facilities_geo.parquet", index=False)
    pd.DataFrame({"state_fips": ["27"], "centers_per_100k": [0.5], "burn_beds_per_100k": [1.0]}).to_parquet(
        tmp_path / "data" / "processed" / "supply_capacity_baseline.parquet", index=False
    )
    pd.DataFrame({"county_fips": ["27123"], "population_total": [100000]}).to_parquet(
        tmp_path / "data" / "processed" / "county_denominators.parquet", index=False
    )


def test_stage_06_outputs_are_structural_not_realtime(tmp_path: Path) -> None:
    _upstream(tmp_path)
    cfg = RuntimeConfig(
        raw={
            "profile": "full",
            "data": {
                "facilities_geo_path": str(tmp_path / "data" / "processed" / "facilities_geo.parquet"),
                "supply_baseline_path": str(tmp_path / "data" / "processed" / "supply_capacity_baseline.parquet"),
                "county_denominators_path": str(tmp_path / "data" / "processed" / "county_denominators.parquet"),
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
    df = pd.read_parquet(tmp_path / "data" / "processed" / "structural_capacity.parquet")
    assert "not_realtime" in df.columns
    assert df["not_realtime"].all()
    assert "capacity_type" in df.columns
    assert (df["capacity_type"] == "structural").all()
