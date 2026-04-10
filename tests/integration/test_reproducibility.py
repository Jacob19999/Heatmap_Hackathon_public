from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_09_story_exports import run


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_story_inputs(tmp_path: Path) -> RuntimeConfig:
    figures_dir = tmp_path / "outputs" / "figures"
    tables_dir = tmp_path / "outputs" / "tables"
    metrics_dir = tmp_path / "outputs" / "metrics"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    (figures_dir / "01_figures_demo_ground_only.png").write_bytes(b"fake-png")
    pd.DataFrame([{"threshold_minutes": 30, "pct_covered": 80.0}]).to_csv(
        tables_dir / "03_tables_demo_ground_only.csv", index=False
    )
    (metrics_dir / "01_findings_ground_only.json").write_text(
        json.dumps(
            {
                "stage_id": "01",
                "question": "Where are facilities and denominators anchored geographically?",
                "finding": "Geography keys and denominator joins were generated.",
                "why_it_matters": "Stable geography joins are required for reproducible metrics.",
                "action_implication": "Use geography outputs as canonical upstream artifacts.",
                "scenario_id": "ground_only",
            }
        ),
        encoding="utf-8",
    )
    (metrics_dir / "03_findings_ground_only.json").write_text(
        json.dumps(
            {
                "stage_id": "03",
                "question": "How unequal is ground travel burden?",
                "finding": "Ground travel burden metrics were generated for configured geography levels.",
                "why_it_matters": "Access burden summaries support stable cross-stage interpretation.",
                "action_implication": "Use burden outputs in downstream pediatric and BEI analyses.",
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


def test_stage_09_reproducibility_for_unchanged_inputs(tmp_path: Path) -> None:
    cfg = _seed_story_inputs(tmp_path)
    first = run(cfg)
    second = run(cfg)

    assert _hash(Path(first["final_findings_summary"])) == _hash(Path(second["final_findings_summary"]))
    assert _hash(Path(first["figure_manifest"])) == _hash(Path(second["figure_manifest"]))
    assert _hash(Path(first["table_manifest"])) == _hash(Path(second["table_manifest"]))
    assert _hash(Path(first["method_notes"])) == _hash(Path(second["method_notes"]))
