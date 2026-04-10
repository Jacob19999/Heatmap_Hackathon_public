"""Integration test for Stage 06 using Stage 02/01 outputs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_06_structural_capacity import run


def _stage01_02_outputs(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    fac = pd.DataFrame({
        "STATE": ["MN", "WI"],
        "county_fips": ["27123", "55025"],
        "ABA_VERIFIED": [True, False],
        "BURN_BEDS": [10, 5],
    })
    supply = pd.DataFrame({
        "state_fips": ["27", "55"],
        "centers_per_100k": [0.5, 0.3],
        "burn_beds_per_100k": [1.0, 0.5],
    })
    county = pd.DataFrame({
        "county_fips": ["27123", "55025"],
        "population_total": [100_000, 200_000],
    })
    fac.to_parquet(processed / "facilities_geo.parquet", index=False)
    supply.to_parquet(processed / "supply_capacity_baseline.parquet", index=False)
    county.to_parquet(processed / "county_denominators.parquet", index=False)


def test_stage_06_runs_with_stage_02_01_outputs(tmp_path: Path) -> None:
    _stage01_02_outputs(tmp_path)
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
    result = run(cfg)
    assert result["ok"] is True
    assert Path(result["dataset"]).exists()
    assert Path(result["finding"]).exists()
    assert Path(result["manifest"]).exists()


def test_stage_06_outputs_are_structural_not_realtime(tmp_path: Path) -> None:
    _stage01_02_outputs(tmp_path)
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
    assert "capacity_type" in df.columns or "not_realtime" in df.columns
    if "not_realtime" in df.columns:
        assert df["not_realtime"].all()
