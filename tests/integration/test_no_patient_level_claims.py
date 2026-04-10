from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from src.results_pipeline.settings import RuntimeConfig
from src.results_pipeline.stages.stage_09_story_exports import run


def _has_forbidden_claim(text: str) -> bool:
    patterns = [
        r"(?<!not )patient-level",
        r"(?<!not )real-time bed availability",
        r"\blive bed availability\b",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def test_stage_09_outputs_avoid_patient_level_or_realtime_claims(tmp_path: Path) -> None:
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
                "question": "Is NIRD standardized and trustworthy for downstream analytics?",
                "finding": "Stage 00 standardized source artifacts for structural access analysis.",
                "why_it_matters": "Structural consistency supports reproducible pipeline outputs.",
                "action_implication": "Use the standardized source as the baseline input.",
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
    result = run(cfg)

    method_notes = Path(result["method_notes"]).read_text(encoding="utf-8")
    final_finding = json.loads(Path(result["finding"]).read_text(encoding="utf-8"))

    assert not _has_forbidden_claim(method_notes)
    assert not _has_forbidden_claim(final_finding["finding"])
    assert not _has_forbidden_claim(final_finding["why_it_matters"])
