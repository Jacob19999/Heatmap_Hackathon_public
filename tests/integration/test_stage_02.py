from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_02_supply_capacity_baseline import run


def _stage01_like_outputs(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    fac = pd.DataFrame({
        "STATE": ["MN", "WI"],
        "state_fips": ["27", "55"],
        "county_fips": ["27123", "55025"],
        "ABA_VERIFIED": [True, False],
        "BURN_BEDS": [10, 5],
        "BURN_ADULT": [True, True],
    })
    county = pd.DataFrame({
        "county_fips": ["27123", "55025"],
        "population_total": [100_000, 200_000],
        "population_child_u18": [25_000, 50_000],
    })
    fac.to_parquet(processed / "facilities_geo.parquet", index=False)
    county.to_parquet(processed / "county_denominators.parquet", index=False)


def test_stage_02_runs_with_stage01_outputs(tmp_path: Path) -> None:
    _stage01_like_outputs(tmp_path)
    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "data": {
                "facilities_geo_path": str(tmp_path / "data" / "processed" / "facilities_geo.parquet"),
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
    assert len(result["tables"]) >= 1
    assert len(result["figures"]) >= 1
    assert Path(result["finding"]).exists()
    assert Path(result["manifest"]).exists()
