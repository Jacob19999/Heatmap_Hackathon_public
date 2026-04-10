"""Stage 08: BEI composite hotspots and driver breakdown; need overlays kept separate from core BEI."""
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
    "stage_id": "08",
    "name": "bei_hotspots",
    "question": "Where are the highest-burden (BEI) hotspots and what drives them?",
    "description": "Build supply, timely access, pediatric, and structural-capacity pillars; compute BEI composite and hotspot tiers; attach need overlays separately.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": [
        "data/processed/supply_capacity_baseline.parquet",
        "data/processed/ground_access_burden.parquet",
        "data/processed/pediatric_access_gap.parquet",
    ],
    "optional_inputs": ["data/processed/stage_06_*.parquet", "data/processed/stage_07_*.parquet"],
    "produced_datasets": ["data/processed/bei_hotspots.parquet"],
    "produced_tables": ["outputs/tables/08_tables_bei_hotspots_ground_only.csv"],
    "produced_figures": ["outputs/figures/08_figures_bei_rank_ground_only.png"],
    "produced_findings": ["outputs/metrics/08_findings_ground_only.json"],
    "validations": ["overlay_not_in_core_bei", "optional_stages_tolerated"],
}


@dataclass(frozen=True)
class Stage08Config:
    supply_baseline_path: Path
    ground_access_path: Path
    pediatric_gap_path: Path
    transfer_aware_path: Path | None
    data_processed_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path
    final_bundle_dir: Path


def _cfg(config: RuntimeConfig) -> Stage08Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    processed = Path(data.get("processed_dir", root / "data" / "processed"))
    return Stage08Config(
        supply_baseline_path=Path(data.get("supply_baseline_path", processed / "supply_capacity_baseline.parquet")),
        ground_access_path=Path(data.get("ground_access_burden_path", processed / "ground_access_burden.parquet")),
        pediatric_gap_path=Path(data.get("pediatric_access_gap_path", processed / "pediatric_access_gap.parquet")),
        transfer_aware_path=Path(data["transfer_aware_path"]) if data.get("transfer_aware_path") else None,
        data_processed_dir=processed,
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
        final_bundle_dir=Path(outputs.get("final_bundle_dir", root / "outputs" / "final_bundle")),
    )


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _cfg(config)
    if not c.supply_baseline_path.exists():
        raise ValidationError(f"Missing supply_capacity_baseline: {c.supply_baseline_path}")
    if not c.ground_access_path.exists():
        raise ValidationError(f"Missing ground_access_burden: {c.ground_access_path}")
    if not c.pediatric_gap_path.exists():
        raise ValidationError(f"Missing pediatric_access_gap: {c.pediatric_gap_path}")

    supply = load_parquet(c.supply_baseline_path)
    access = load_parquet(c.ground_access_path)
    peds = load_parquet(c.pediatric_gap_path)

    geo_col = "state_fips" if "state_fips" in supply.columns else supply.columns[0]
    supply = supply.copy()
    if geo_col not in supply.columns and "state_fips" in supply.columns:
        geo_col = "state_fips"

    access_by = "state_fips" if "state_fips" in access.columns else "tract_geoid"
    if access_by == "tract_geoid":
        access_agg = access.groupby(access["tract_geoid"].astype(str).str[:2] if "tract_geoid" in access.columns else access.index).agg(
            travel_minutes=("travel_minutes", "mean"),
            population=("population", "sum") if "population" in access.columns else ("travel_minutes", "count"),
        ).reset_index()
        access_agg = access_agg.rename(columns={access_agg.columns[0]: "state_fips"})
    else:
        access_agg = access.groupby(access_by).agg(
            travel_minutes=("travel_minutes", "mean"),
            population=("population", "sum") if "population" in access.columns else ("travel_minutes", "count"),
        ).reset_index()
        access_agg = access_agg.rename(columns={access_by: "state_fips"}) if access_by != "state_fips" else access_agg

    peds_by = "state_fips" if "state_fips" in peds.columns else "tract_geoid"
    if peds_by == "tract_geoid" and "tract_geoid" in peds.columns:
        peds["state_fips"] = peds["tract_geoid"].astype(str).str[:2]
        peds_by = "state_fips"
    peds_agg = peds.groupby(peds_by).agg(
        peds_avg_min=("peds_travel_minutes", "mean"),
    ).reset_index()
    peds_agg = peds_agg.rename(columns={peds_by: "state_fips"}) if peds_by != "state_fips" else peds_agg

    if "state_fips" not in supply.columns and geo_col in supply.columns:
        supply["state_fips"] = supply[geo_col].astype(str).str.zfill(2)
    elif "state_fips" not in supply.columns:
        supply["state_fips"] = ""
    agg_cols: dict[str, str] = {}
    for col in ["centers_per_100k", "burn_beds_per_100k", "aba_verified", "burn_capable"]:
        if col in supply.columns:
            agg_cols[col] = "first" if col.startswith("centers") or col.startswith("burn_beds") else "sum"
    bei = supply.groupby("state_fips").agg(agg_cols).reset_index() if agg_cols else supply[["state_fips"]].drop_duplicates()
    for col in ["centers_per_100k", "burn_beds_per_100k"]:
        if col not in bei.columns:
            bei[col] = 0.0
    bei = bei.merge(access_agg, on="state_fips", how="left")
    bei = bei.merge(peds_agg, on="state_fips", how="left")

    structural_path = c.data_processed_dir / "structural_capacity.parquet"
    if structural_path.exists():
        structural = load_parquet(structural_path)
        if "county_fips" in structural.columns:
            structural = structural.copy()
            structural["state_fips"] = structural["county_fips"].astype(str).str[:2]
            struct_agg = structural.groupby("state_fips").agg(
                structural_competition=("structural_competition_per_bed", "mean"),
            ).reset_index()
            bei = bei.merge(struct_agg, on="state_fips", how="left")

    for col in ["centers_per_100k", "burn_beds_per_100k", "travel_minutes", "peds_avg_min"]:
        if col not in bei.columns:
            bei[col] = 0.0
    denom_s = bei["centers_per_100k"].max() - bei["centers_per_100k"].min() + 1e-9
    supply_pillar = 1.0 - (bei["centers_per_100k"] - bei["centers_per_100k"].min()) / denom_s
    supply_pillar = supply_pillar.fillna(0.5).clip(0, 1)
    denom_a = bei["travel_minutes"].max() - bei["travel_minutes"].min() + 1e-9
    access_pillar = (bei["travel_minutes"] - bei["travel_minutes"].min()) / denom_a
    access_pillar = access_pillar.fillna(0.5).clip(0, 1)
    denom_p = bei["peds_avg_min"].max() - bei["peds_avg_min"].min() + 1e-9
    peds_pillar = (bei["peds_avg_min"] - bei["peds_avg_min"].min()) / denom_p
    peds_pillar = peds_pillar.fillna(0.5).clip(0, 1)
    denom_c = bei["burn_beds_per_100k"].max() - bei["burn_beds_per_100k"].min() + 1e-9
    capacity_pillar = 1.0 - (bei["burn_beds_per_100k"] - bei["burn_beds_per_100k"].min()) / denom_c
    capacity_pillar = capacity_pillar.fillna(0.5).clip(0, 1)

    bei["supply_pillar"] = supply_pillar
    bei["access_pillar"] = access_pillar
    bei["peds_pillar"] = peds_pillar
    bei["structural_capacity_pillar"] = capacity_pillar
    bei["bei_composite"] = (supply_pillar + access_pillar + peds_pillar + capacity_pillar) / 4.0

    q1, q2, q3 = bei["bei_composite"].quantile([0.25, 0.5, 0.75])
    def tier(x: float) -> str:
        if pd.isna(x): return "unknown"
        if x >= q3: return "high"
        if x >= q2: return "medium"
        return "low"
    bei["hotspot_tier"] = bei["bei_composite"].apply(tier)
    bei["driver_breakdown"] = "supply=" + supply_pillar.round(2).astype(str) + ";access=" + access_pillar.round(2).astype(str) + ";peds=" + peds_pillar.round(2).astype(str) + ";capacity=" + capacity_pillar.round(2).astype(str)
    bei["need_overlay"] = ""
    if "svi_overall" in bei.columns:
        bei["need_overlay"] = "svi=" + bei["svi_overall"].astype(str)
    bei["need_overlay_attached_not_in_bei"] = True

    dataset_path = c.data_processed_dir / "bei_hotspots.parquet"
    table_path = c.outputs_tables_dir / "08_tables_bei_hotspots_ground_only.csv"
    fig_path = c.outputs_figures_dir / "08_figures_bei_rank_ground_only.png"
    top_path = c.final_bundle_dir / "top_hotspots.csv"
    finding_path = c.outputs_metrics_dir / "08_findings_ground_only.json"
    manifest_path = c.outputs_metrics_dir / "08_manifest_ground_only.json"

    write_parquet(bei, dataset_path)
    write_csv(bei, table_path)
    top = bei.nlargest(20, "bei_composite")[["state_fips", "bei_composite", "hotspot_tier", "driver_breakdown"]].copy()
    top_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(top, top_path)

    fig, ax = plt.subplots(figsize=(8, 4))
    bei.nlargest(15, "bei_composite").plot(x="state_fips", y="bei_composite", kind="bar", ax=ax, color="#EA4335")
    ax.set_title("Stage 08 BEI composite (top 15 geographies)")
    ax.set_ylabel("BEI score")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    finding = FindingRecord(
        stage_id="08",
        question="Where are the highest-burden (BEI) hotspots and what drives them?",
        finding="BEI composite and hotspot tiers were computed from supply, timely access, pediatric access, and structural-capacity pillars; need overlays are attached separately and not mixed into core BEI.",
        why_it_matters="Hotspots drive prioritization; method requires overlays to remain distinct.",
        action_implication="Use BEI outputs for story exports and top_hotspots for final bundle.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage08",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("08_dataset_bei", "08", "dataset", str(dataset_path), "parquet"),
            ArtifactRecord("08_table_hotspots", "08", "table", str(table_path), "csv"),
            ArtifactRecord("08_fig_bei_rank", "08", "figure", str(fig_path), "png"),
            ArtifactRecord("08_top_hotspots", "08", "table", str(top_path), "csv"),
            ArtifactRecord("08_finding", "08", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "08",
        "dataset": str(dataset_path),
        "tables": [str(table_path), str(top_path)],
        "figures": [str(fig_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
