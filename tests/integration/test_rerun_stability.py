from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_09_story_exports import run


def _seed_story_inputs(tmp_path: Path) -> RuntimeConfig:
    figures_dir = tmp_path / "outputs" / "figures"
    tables_dir = tmp_path / "outputs" / "tables"
    metrics_dir = tmp_path / "outputs" / "metrics"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    (figures_dir / "00_figures_demo_ground_only.png").write_bytes(b"fake-png")
    pd.DataFrame([{"metric": "rows", "value": 1}]).to_csv(
        tables_dir / "00_tables_demo_ground_only.csv", index=False
    )
    (metrics_dir / "00_findings_ground_only.json").write_text(
        json.dumps(
            {
                "stage_id": "00",
                "question": "Is the source data standardized?",
                "finding": "Stage 00 generated standardized source artifacts.",
                "why_it_matters": "Stable source quality is required for reproducible outputs.",
                "action_implication": "Proceed with staged analytics using the standardized source.",
                "scenario_id": "ground_only",
            }
        ),
        encoding="utf-8",
    )

    return RuntimeConfig(
        raw={
            "profile": "mvp",
            "scenario": "ground_only",
            "outputs": {
                "figures_dir": str(figures_dir),
                "tables_dir": str(tables_dir),
                "metrics_dir": str(metrics_dir),
                "final_bundle_dir": str(tmp_path / "outputs" / "final_bundle"),
            },
        },
        source_paths=[],
    )


def test_stage_09_rerun_stability_for_paths_and_schemas(tmp_path: Path) -> None:
    cfg = _seed_story_inputs(tmp_path)
    first = run(cfg)
    second = run(cfg)

    assert first["final_bundle"] == second["final_bundle"]
    assert first["final_findings_summary"] == second["final_findings_summary"]
    assert first["figure_manifest"] == second["figure_manifest"]
    assert first["table_manifest"] == second["table_manifest"]

    first_findings = pd.read_csv(Path(first["final_findings_summary"]))
    second_findings = pd.read_csv(Path(second["final_findings_summary"]))
    first_fig_manifest = pd.read_csv(Path(first["figure_manifest"]))
    second_fig_manifest = pd.read_csv(Path(second["figure_manifest"]))
    first_tbl_manifest = pd.read_csv(Path(first["table_manifest"]))
    second_tbl_manifest = pd.read_csv(Path(second["table_manifest"]))

    assert first_findings.columns.tolist() == second_findings.columns.tolist()
    assert first_fig_manifest.columns.tolist() == second_fig_manifest.columns.tolist()
    assert first_tbl_manifest.columns.tolist() == second_tbl_manifest.columns.tolist()
