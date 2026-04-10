from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_09_story_exports import run
from src.results_pipeline.utils.validation import ValidationError


def test_stage_09_requires_findings_coverage_for_final_artifacts(tmp_path: Path) -> None:
    figures_dir = tmp_path / "outputs" / "figures"
    tables_dir = tmp_path / "outputs" / "tables"
    metrics_dir = tmp_path / "outputs" / "metrics"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    (figures_dir / "03_figures_demo_ground_only.png").write_bytes(b"fake-png")
    pd.DataFrame([{"threshold_minutes": 30, "pct_covered": 50.0}]).to_csv(
        tables_dir / "03_tables_demo_ground_only.csv", index=False
    )
    (metrics_dir / "00_findings_ground_only.json").write_text(
        json.dumps(
            {
                "stage_id": "00",
                "question": "Is NIRD standardized and trustworthy for downstream analytics?",
                "finding": "Stage 00 standardized source fields for downstream use.",
                "why_it_matters": "Source consistency is required for reproducible outputs.",
                "action_implication": "Use normalized source outputs as the canonical base.",
                "scenario_id": "ground_only",
            }
        ),
        encoding="utf-8",
    )

    cfg = RuntimeConfig(
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

    with pytest.raises(ValidationError):
        run(cfg)
