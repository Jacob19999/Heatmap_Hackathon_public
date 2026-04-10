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

    (figures_dir / "02_figures_demo_ground_only.png").write_bytes(b"fake-png")
    pd.DataFrame([{"state_fips": "27", "centers_per_100k": 1.2}]).to_csv(
        tables_dir / "02_tables_demo_ground_only.csv", index=False
    )
    (metrics_dir / "02_findings_ground_only.json").write_text(
        json.dumps(
            {
                "stage_id": "02",
                "question": "How is burn supply distributed per capita?",
                "finding": "Supply distribution artifacts were generated for the configured scenario.",
                "why_it_matters": "Stable supply metrics are prerequisites for reproducible BEI construction.",
                "action_implication": "Use Stage 02 outputs for downstream burden and hotspot stages.",
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


def _normalized_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.pop("created_at", None)
    return manifest


def test_stage_09_manifest_stability_across_reruns(tmp_path: Path) -> None:
    cfg = _seed_story_inputs(tmp_path)
    first = run(cfg)
    second = run(cfg)

    first_manifest = _normalized_manifest(Path(first["manifest"]))
    second_manifest = _normalized_manifest(Path(second["manifest"]))
    assert first_manifest == second_manifest
