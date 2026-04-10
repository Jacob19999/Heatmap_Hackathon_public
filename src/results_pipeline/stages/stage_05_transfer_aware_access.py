"""Stage 05: Transfer-aware system access — direct vs stabilize-and-transfer paths."""
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
    "stage_id": "05",
    "name": "transfer_aware_access",
    "question": "How does transfer-aware access compare to direct-only access?",
    "description": "Define stabilization candidates; compute direct and transfer paths with configurable penalty; compare metrics.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": ["data/processed/ground_access_burden.parquet", "data/processed/facilities_geo.parquet"],
    "produced_datasets": ["data/processed/transfer_aware_access.parquet"],
    "produced_tables": ["outputs/tables/05_tables_transfer_comparison_ground_only.csv"],
    "produced_figures": ["outputs/figures/05_figures_transfer_aware_ground_only.png"],
    "produced_findings": ["outputs/metrics/05_findings_ground_only.json"],
    "validations": ["transfer_penalty_consistency", "artifact_presence"],
}


@dataclass(frozen=True)
class Stage05Config:
    ground_access_path: Path
    facilities_geo_path: Path
    data_processed_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path
    transfer_penalty_minutes: float


def _cfg(config: RuntimeConfig) -> Stage05Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    processed = Path(data.get("processed_dir", root / "data" / "processed"))
    routing = config.raw.get("routing", {})
    return Stage05Config(
        ground_access_path=Path(data.get("ground_access_burden_path", processed / "ground_access_burden.parquet")),
        facilities_geo_path=Path(data.get("facilities_geo_path", processed / "facilities_geo.parquet")),
        data_processed_dir=processed,
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
        transfer_penalty_minutes=float(routing.get("transfer_penalty_minutes", 30.0)),
    )


def _stabilization_candidates(fac: pd.DataFrame) -> pd.Series:
    """Facilities that can stabilize before transfer (e.g. have burn capability but not necessarily ABA verified)."""
    burn = pd.Series(False, index=fac.index)
    for c in ("BURN_ADULT", "BURN_PEDS", "ABA_VERIFIED"):
        if c in fac.columns:
            burn = burn | fac[c].fillna(False).astype(bool)
    return burn


def _definitive_candidates(fac: pd.DataFrame) -> pd.Series:
    """ABA verified or otherwise definitive burn centers."""
    if "ABA_VERIFIED" in fac.columns:
        return fac["ABA_VERIFIED"].fillna(False).astype(bool)
    if "facility_class" in fac.columns:
        return fac["facility_class"].astype(str).str.contains("burn|verified", case=False, na=False)
    return pd.Series(False, index=fac.index)


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _cfg(config)
    if not c.ground_access_path.exists():
        raise ValidationError(f"Missing ground_access_burden: {c.ground_access_path}")
    if not c.facilities_geo_path.exists():
        raise ValidationError(f"Missing facilities_geo: {c.facilities_geo_path}")

    access = load_parquet(c.ground_access_path)
    fac = load_parquet(c.facilities_geo_path)

    stab_mask = _stabilization_candidates(fac)
    def_mask = _definitive_candidates(fac)
    access = access.copy()
    access["direct_minutes"] = access["travel_minutes"]
    access["transfer_penalty_minutes"] = c.transfer_penalty_minutes
    access["transfer_aware_minutes"] = access["direct_minutes"] + c.transfer_penalty_minutes
    access["stabilization_available"] = stab_mask.any()
    access["definitive_available"] = def_mask.any()

    by_col = "state_fips" if "state_fips" in access.columns else (access.columns[0] if len(access.columns) else "tract_geoid")
    if by_col not in access.columns:
        by_col = access.columns[0]
    pop_col = "population" if "population" in access.columns else "total_pop"
    if pop_col not in access.columns:
        access["population"] = 1
        pop_col = "population"
    comp = access.groupby(by_col).agg(
        direct_avg=("direct_minutes", "mean"),
        transfer_aware_avg=("transfer_aware_minutes", "mean"),
        pop=(pop_col, "sum"),
    ).reset_index()
    comp["penalty_used_minutes"] = c.transfer_penalty_minutes

    dataset_path = c.data_processed_dir / "transfer_aware_access.parquet"
    table_path = c.outputs_tables_dir / "05_tables_transfer_comparison_ground_only.csv"
    fig_path = c.outputs_figures_dir / "05_figures_transfer_aware_ground_only.png"
    finding_path = c.outputs_metrics_dir / "05_findings_ground_only.json"
    manifest_path = c.outputs_metrics_dir / "05_manifest_ground_only.json"

    write_parquet(access, dataset_path)
    write_csv(comp, table_path)

    fig, ax = plt.subplots(figsize=(8, 4))
    top = comp.nlargest(15, "transfer_aware_avg")
    top.plot(x=by_col, y=["direct_avg", "transfer_aware_avg"], kind="bar", ax=ax, color=["#34A853", "#FBBC04"])
    ax.set_title("Stage 05 Direct vs transfer-aware avg travel minutes")
    ax.set_ylabel("minutes")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    finding = FindingRecord(
        stage_id="05",
        question="How does transfer-aware access compare to direct-only access?",
        finding="Transfer penalty was applied from config; direct and transfer-aware metrics were compared by geography.",
        why_it_matters="Transfer-aware access reflects real-world stabilization pathways.",
        action_implication="Use transfer-aware metrics in BEI when transfer scenarios are in scope.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage05",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("05_dataset_transfer", "05", "dataset", str(dataset_path), "parquet"),
            ArtifactRecord("05_table_comparison", "05", "table", str(table_path), "csv"),
            ArtifactRecord("05_fig_transfer", "05", "figure", str(fig_path), "png"),
            ArtifactRecord("05_finding", "05", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "05",
        "dataset": str(dataset_path),
        "tables": [str(table_path)],
        "figures": [str(fig_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
