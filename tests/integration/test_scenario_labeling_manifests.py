from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_07_air_sensitivity import run


def test_stage_07_manifest_and_finding_are_scenario_labeled(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "tract_geoid": ["27123000100"],
            "state_fips": ["27"],
            "travel_minutes": [50.0],
            "total_pop": [4000],
        }
    ).to_parquet(processed / "ground_access_burden.parquet", index=False)

    cfg = RuntimeConfig(
        raw={
            "profile": "full",
            "scenario": "ground_plus_air",
            "data": {
                "ground_access_burden_path": str(processed / "ground_access_burden.parquet"),
                "processed_dir": str(processed),
            },
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
            "air_assumptions": {"enabled": True, "air_cap_minutes": 60, "air_speed_factor": 0.4},
        },
        source_paths=[],
    )

    result = run(cfg)
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    finding = json.loads(Path(result["finding"]).read_text(encoding="utf-8"))

    assert finding["scenario_id"] == "ground_plus_air"
    for artifact in manifest["artifacts"]:
        assert artifact.get("scenario_id") == "ground_plus_air"
        assert "ground_plus_air" in artifact["path"]
