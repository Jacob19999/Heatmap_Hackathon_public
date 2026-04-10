from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_00_data_audit import STAGE_META, run


def _make_sample_nird(path: Path) -> None:
    df = pd.DataFrame(
        {
            "AHA_ID": ["300", "301"],
            "HOSPITAL_NAME": ["Hosp C", "Hosp D"],
            "STATE": ["MN", "IA"],
            "ZIP_CODE": ["55001", "50010"],
            "BURN_ADULT": ["1", "0"],
            "BURN_PEDS": ["0", "1"],
            "TRAUMA_ADULT": ["1", "0"],
            "ABA_VERIFIED": ["1", "0"],
            "BC_STATE_DESIGNATED": ["1", "0"],
            "TOTAL_BEDS": ["120", "200"],
            "BURN_BEDS": ["12", "4"],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data Table NIRD 20230130")


def test_stage_00_meta_contains_required_contract_fields() -> None:
    required = [
        "stage_id",
        "name",
        "question",
        "description",
        "replaces_notebooks",
        "required_inputs",
        "produced_datasets",
        "produced_tables",
        "produced_figures",
        "produced_findings",
        "validations",
    ]
    for field in required:
        assert field in STAGE_META


def test_stage_00_emits_contract_artifacts(tmp_path: Path) -> None:
    nird = tmp_path / "nird_contract.xlsx"
    _make_sample_nird(nird)
    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "data": {"nird_path": str(nird), "interim_dir": str(tmp_path / "data" / "interim")},
            "outputs": {
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
            },
        },
        source_paths=[],
    )
    result = run(cfg)
    assert Path(result["dataset"]).exists()
    for table in result["tables"]:
        assert Path(table).exists()
    for figure in result["figures"]:
        assert Path(figure).exists()
    assert Path(result["finding"]).exists()
    manifest_path = Path(result["manifest"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifacts"], "manifest should include artifacts"
