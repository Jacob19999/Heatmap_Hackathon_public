from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.orchestrator import run_pipeline
from src.results_pipeline.stages.stage_00_data_audit import run


def _make_sample_nird(path: Path) -> None:
    df = pd.DataFrame(
        {
            "AHA_ID": ["100", "100", "200"],
            "HOSPITAL_NAME": ["Hosp A", "Hosp A", "Hosp B"],
            "STATE": ["MN", "MN", "WI"],
            "ZIP_CODE": ["55101", "55101", "53703"],
            "BURN_ADULT": ["Yes", "Yes", "No"],
            "BURN_PEDS": ["", "1", "0"],
            "TRAUMA_ADULT": ["1", "1", ""],
            "ABA_VERIFIED": ["1", "1", "0"],
            "BC_STATE_DESIGNATED": ["1", "1", "0"],
            "TOTAL_BEDS": ["100", "100", "250"],
            "BURN_BEDS": ["10", "10", "0"],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data Table NIRD 20230130")


def test_stage_00_runs_independently(tmp_path: Path) -> None:
    nird = tmp_path / "nird_sample.xlsx"
    _make_sample_nird(nird)
    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "data": {
                "nird_path": str(nird),
                "interim_dir": str(tmp_path / "data" / "interim"),
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


def test_stage_00_failure_halts_downstream_pipeline(tmp_path: Path) -> None:
    cfg = RuntimeConfig(
        raw={
            "profile": "stage",
            "stages": ["00", "01"],
            "data": {"nird_path": str(tmp_path / "missing.xlsx")},
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
        },
        source_paths=[],
    )
    result = run_pipeline(cfg)
    assert result["ok"] is False
    assert result["failed_stage"] == "00"
