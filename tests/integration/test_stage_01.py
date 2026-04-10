from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_01_geography_enrichment import run


def _stage00_like_dataset(path: Path) -> None:
    df = pd.DataFrame(
        {
            "AHA_ID": ["100", "200"],
            "HOSPITAL_NAME": ["Hosp A", "Hosp B"],
            "STATE": ["MN", "WI"],
            "COUNTY_FIPS": ["27123", "55025"],
            "TRACT_FIPS": ["27123000100", "55025000200"],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def test_stage_01_runs_with_stage00_outputs(tmp_path: Path) -> None:
    nird_clean = tmp_path / "data" / "interim" / "nird_clean.parquet"
    _stage00_like_dataset(nird_clean)

    county = pd.DataFrame({"county_fips": ["27123", "55025"], "population_total": [100000, 200000], "population_child_u18": [25000, 50000]})
    tract = pd.DataFrame({"tract_geoid": ["27123000100", "55025000200"], "population_total": [4000, 5000], "population_child_u18": [1000, 1200]})
    ruca = pd.DataFrame({"tract_geoid": ["27123000100", "55025000200"], "ruca_primary_code": [2, 5]})
    county_path = tmp_path / "ext" / "county.csv"
    tract_path = tmp_path / "ext" / "tract.csv"
    ruca_path = tmp_path / "ext" / "ruca.csv"
    county_path.parent.mkdir(parents=True, exist_ok=True)
    county.to_csv(county_path, index=False)
    tract.to_csv(tract_path, index=False)
    ruca.to_csv(ruca_path, index=False)

    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "data": {
                "nird_clean_path": str(nird_clean),
                "processed_dir": str(tmp_path / "data" / "processed"),
                "external": {
                    "county_denominators": str(county_path),
                    "tract_denominators": str(tract_path),
                    "ruca": str(ruca_path),
                },
            },
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
            "validation": {"strict_geography": True},
        },
        source_paths=[],
    )
    result = run(cfg)
    assert result["ok"] is True
    assert Path(result["dataset"]).exists()
    assert Path(result["county_denom"]).exists()
    assert Path(result["tract_denom"]).exists()
    assert Path(result["finding"]).exists()
    assert Path(result["manifest"]).exists()
