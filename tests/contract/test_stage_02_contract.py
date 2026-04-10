from __future__ import annotations

from src.results_pipeline.stages.stage_02_supply_capacity_baseline import STAGE_META


def test_stage_02_contract_metadata() -> None:
    assert STAGE_META["stage_id"] == "02"
    assert "supply_capacity_baseline" in STAGE_META["name"]
    assert "produced_datasets" in STAGE_META
    assert "produced_tables" in STAGE_META
    assert "produced_figures" in STAGE_META
    assert any("02_tables" in t for t in STAGE_META["produced_tables"])
    assert any("02_figures" in f for f in STAGE_META["produced_figures"])
