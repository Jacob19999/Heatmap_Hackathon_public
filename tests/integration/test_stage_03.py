from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_03_ground_access_burden import run


def _stage02_upstream(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    cache = tmp_path / "data" / "cache"
    processed.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    fac = pd.DataFrame({
        "STATE": ["MN"],
        "state_fips": ["27"],
        "county_fips": ["27123"],
        "latitude": [44.95],
        "longitude": [-93.09],
        "BURN_ADULT": [True],
    })
    tracts = pd.DataFrame({
        "tract_geoid": ["27123000100", "27123000200"],
        "centroid_lat": [44.96, 44.94],
        "centroid_lon": [-93.08, -93.10],
        "total_pop": [4000, 5000],
    })
    fac.to_parquet(processed / "facilities_geo.parquet", index=False)
    tracts.to_parquet(processed / "tract_denominators.parquet", index=False)


def test_stage_03_runs_with_upstream_artifacts(tmp_path: Path) -> None:
    _stage02_upstream(tmp_path)
    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "data": {
                "facilities_geo_path": str(tmp_path / "data" / "processed" / "facilities_geo.parquet"),
                "tract_denominators_path": str(tmp_path / "data" / "processed" / "tract_denominators.parquet"),
                "processed_dir": str(tmp_path / "data" / "processed"),
                "cache_dir": str(tmp_path / "data" / "cache"),
            },
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
            "routing": {"km_per_minute": 0.8},
        },
        source_paths=[],
    )
    result = run(cfg)
    assert result["ok"] is True
    assert Path(result["dataset"]).exists()
    assert Path(result["finding"]).exists()
    assert Path(result["manifest"]).exists()
