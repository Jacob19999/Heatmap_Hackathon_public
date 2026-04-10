from __future__ import annotations

from src.results_pipeline.stages import (
    stage_00_data_audit,
    stage_01_geography_enrichment,
    stage_02_supply_capacity_baseline,
    stage_03_ground_access_burden,
    stage_04_pediatric_access_gap,
    stage_05_transfer_aware_access,
    stage_06_structural_capacity,
    stage_07_air_sensitivity,
    stage_08_bei_hotspots,
    stage_09_story_exports,
)


def test_all_stages_declare_notebook_replacement_mapping() -> None:
    metas = [
        stage_00_data_audit.STAGE_META,
        stage_01_geography_enrichment.STAGE_META,
        stage_02_supply_capacity_baseline.STAGE_META,
        stage_03_ground_access_burden.STAGE_META,
        stage_04_pediatric_access_gap.STAGE_META,
        stage_05_transfer_aware_access.STAGE_META,
        stage_06_structural_capacity.STAGE_META,
        stage_07_air_sensitivity.STAGE_META,
        stage_08_bei_hotspots.STAGE_META,
        stage_09_story_exports.STAGE_META,
    ]
    for meta in metas:
        replaces = meta.get("replaces_notebooks")
        assert isinstance(replaces, list) and replaces, f"{meta.get('stage_id')} missing replaces_notebooks mapping"
