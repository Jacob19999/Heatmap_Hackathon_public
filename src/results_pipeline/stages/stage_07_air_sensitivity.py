"""Stage 07: Air sensitivity scenario — ground-only baseline vs ground-plus-air; scenario-labeled outputs only."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from ..contracts.artifacts import ArtifactManifest, ArtifactRecord, FindingRecord
from ..io.loaders import load_parquet
from ..io.writers import write_csv, write_finding, write_manifest, write_parquet
from ..settings import RuntimeConfig
from ..utils.validation import ValidationError

STAGE_META: dict[str, Any] = {
    "stage_id": "07",
    "name": "air_sensitivity",
    "question": "How sensitive are access results to conditional air transport?",
    "description": "Compare ground-only baseline to ground-plus-air scenario; all outputs are scenario-labeled; never overwrites ground-only baseline artifacts.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": ["data/processed/ground_access_burden.parquet"],
    "produced_datasets": ["data/processed/air_sensitivity_{scenario}.parquet"],
    "produced_tables": ["outputs/tables/07_tables_air_sensitivity_{scenario}.csv"],
    "produced_figures": ["outputs/figures/07_figures_air_sensitivity_{scenario}.png"],
    "produced_findings": ["outputs/metrics/07_findings_{scenario}.json"],
    "validations": ["scenario_labeled", "no_overwrite_baseline"],
}


@dataclass(frozen=True)
class Stage07Config:
    ground_access_path: Path
    data_processed_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path
    scenario_id: str
    air_cap_minutes: float
    air_speed_factor: float


def _cfg(config: RuntimeConfig) -> Stage07Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    processed = Path(data.get("processed_dir", root / "data" / "processed"))
    scenario_id = config.scenario
    air = config.raw.get("air_assumptions", {}) or config.raw.get("routing", {})
    return Stage07Config(
        ground_access_path=Path(data.get("ground_access_burden_path", processed / "ground_access_burden.parquet")),
        data_processed_dir=processed,
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
        scenario_id=scenario_id,
        air_cap_minutes=float(air.get("air_cap_minutes", 60.0)),
        air_speed_factor=float(air.get("air_speed_factor", 0.4)),
    )


def run(config: RuntimeConfig) -> dict[str, Any]:
    sc = _cfg(config)
    if not sc.ground_access_path.exists():
        raise ValidationError(f"Missing ground_access_burden: {sc.ground_access_path}")

    scenario_id = sc.scenario_id
    access = load_parquet(sc.ground_access_path).copy()

    if scenario_id == "ground_plus_air":
        access["travel_minutes_ground"] = access["travel_minutes"]
        access["travel_minutes_air_capped"] = access["travel_minutes"].clip(upper=sc.air_cap_minutes)
        access["travel_minutes"] = (access["travel_minutes_ground"] * (1 - sc.air_speed_factor)).clip(upper=sc.air_cap_minutes)
        access["scenario"] = "ground_plus_air"
    else:
        access["travel_minutes_ground"] = access["travel_minutes"]
        access["scenario"] = "ground_only"

    dataset_path = sc.data_processed_dir / f"air_sensitivity_{scenario_id}.parquet"
    table_path = sc.outputs_tables_dir / f"07_tables_air_sensitivity_{scenario_id}.csv"
    fig_path = sc.outputs_figures_dir / f"07_figures_air_sensitivity_{scenario_id}.png"
    finding_path = sc.outputs_metrics_dir / f"07_findings_{scenario_id}.json"
    manifest_path = sc.outputs_metrics_dir / f"07_manifest_{scenario_id}.json"

    write_parquet(access, dataset_path)
    write_csv(access.head(500), table_path)

    fig, ax = plt.subplots(figsize=(8, 4))
    group_col = "state_fips" if "state_fips" in access.columns else access.columns[0]
    if "travel_minutes_ground" in access.columns and scenario_id == "ground_plus_air":
        comp = access.groupby(group_col).agg(
            ground=("travel_minutes_ground", "mean"),
            scenario=("travel_minutes", "mean"),
        ).reset_index()
        comp = comp.nlargest(15, "ground")
        comp.plot(x=group_col, y=["ground", "scenario"], kind="bar", ax=ax, color=["#34A853", "#4285F4"])
        ax.set_title(f"Stage 07 Air sensitivity (scenario={scenario_id})\nGround vs scenario travel minutes")
    else:
        by_geo = access.groupby(group_col)["travel_minutes"].mean().reset_index().nlargest(15, "travel_minutes")
        by_geo.plot(x=group_col, y="travel_minutes", kind="bar", ax=ax, color="#4285F4", legend=False)
        ax.set_title(f"Stage 07 Baseline (scenario={scenario_id})")
    ax.set_ylabel("minutes")
    fig.tight_layout()
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    finding = FindingRecord(
        stage_id="07",
        question="How sensitive are access results to conditional air transport?",
        finding=f"Stage 07 produced scenario-labeled outputs for scenario_id={scenario_id}. Ground-only baseline artifacts are not modified by this stage.",
        why_it_matters="Air transport is a scenario/sensitivity layer only; baseline remains ground-only for comparability.",
        action_implication="Use air sensitivity outputs only when scenario is ground_plus_air; do not overwrite ground-only deliverables.",
        scenario_id=scenario_id,
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage07",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("07_dataset_air", "07", "dataset", str(dataset_path), "parquet", scenario_id=scenario_id),
            ArtifactRecord("07_table_air", "07", "table", str(table_path), "csv", scenario_id=scenario_id),
            ArtifactRecord("07_fig_air", "07", "figure", str(fig_path), "png", scenario_id=scenario_id),
            ArtifactRecord("07_finding", "07", "finding", str(finding_path), "json", scenario_id=scenario_id),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "07",
        "scenario_id": scenario_id,
        "dataset": str(dataset_path),
        "tables": [str(table_path)],
        "figures": [str(fig_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
