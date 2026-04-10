from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_01_geography_enrichment import run
from src.results_pipeline.utils.validation import ValidationError


def test_stage_01_fails_with_missing_state_column(tmp_path: Path) -> None:
    bad = pd.DataFrame({"AHA_ID": ["1"], "HOSPITAL_NAME": ["Only Hosp"]})
    nird_clean = tmp_path / "data" / "interim" / "nird_clean.parquet"
    nird_clean.parent.mkdir(parents=True, exist_ok=True)
    bad.to_parquet(nird_clean, index=False)

    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "data": {"nird_clean_path": str(nird_clean)},
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
        },
        source_paths=[],
    )
    with pytest.raises(ValidationError):
        run(cfg)


def test_stage_01_fails_with_unmapped_state_when_strict(tmp_path: Path) -> None:
    bad = pd.DataFrame({"AHA_ID": ["1"], "HOSPITAL_NAME": ["Only Hosp"], "STATE": ["XX"]})
    nird_clean = tmp_path / "data" / "interim" / "nird_clean.parquet"
    nird_clean.parent.mkdir(parents=True, exist_ok=True)
    bad.to_parquet(nird_clean, index=False)

    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "data": {"nird_clean_path": str(nird_clean)},
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
            "validation": {"strict_geography": True},
        },
        source_paths=[],
    )
    with pytest.raises(ValidationError):
        run(cfg)
