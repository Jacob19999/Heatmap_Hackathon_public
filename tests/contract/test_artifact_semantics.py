from __future__ import annotations

from src.results_pipeline.contracts.schemas import validate_manifest_payload


def test_manifest_artifact_type_format_semantics_accept_valid_pairs() -> None:
    ok, errors = validate_manifest_payload(
        {
            "run_id": "run_semantics_ok",
            "profile": "mvp",
            "created_at": "2026-03-16T00:00:00Z",
            "artifacts": [
                {
                    "artifact_id": "a_dataset",
                    "stage_id": "03",
                    "artifact_type": "dataset",
                    "path": "data/processed/ground_access_burden.parquet",
                    "format": "parquet",
                },
                {
                    "artifact_id": "a_table",
                    "stage_id": "03",
                    "artifact_type": "table",
                    "path": "outputs/tables/03_tables_coverage_threshold_ground_only.csv",
                    "format": "csv",
                },
                {
                    "artifact_id": "a_figure",
                    "stage_id": "03",
                    "artifact_type": "figure",
                    "path": "outputs/figures/03_figures_rural_urban_burden_ground_only.png",
                    "format": "png",
                },
                {
                    "artifact_id": "a_finding",
                    "stage_id": "03",
                    "artifact_type": "finding",
                    "path": "outputs/metrics/03_findings_ground_only.json",
                    "format": "json",
                },
            ],
        }
    )
    assert ok is True
    assert errors == []


def test_manifest_artifact_type_format_semantics_reject_invalid_pairs() -> None:
    ok, errors = validate_manifest_payload(
        {
            "run_id": "run_semantics_bad",
            "profile": "mvp",
            "created_at": "2026-03-16T00:00:00Z",
            "artifacts": [
                {
                    "artifact_id": "bad_figure_csv",
                    "stage_id": "09",
                    "artifact_type": "figure",
                    "path": "outputs/final_bundle/figure_manifest.csv",
                    "format": "csv",
                },
                {
                    "artifact_id": "bad_finding_csv",
                    "stage_id": "09",
                    "artifact_type": "finding",
                    "path": "outputs/metrics/09_findings_ground_only.csv",
                    "format": "csv",
                },
            ],
        }
    )
    assert ok is False
    assert any("format_for_type:figure:csv" in err for err in errors)
    assert any("format_for_type:finding:csv" in err for err in errors)
