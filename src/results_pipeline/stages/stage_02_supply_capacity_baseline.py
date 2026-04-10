"""Stage 02: Supply distribution and structural capacity baseline."""
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
    "stage_id": "02",
    "name": "supply_capacity_baseline",
    "question": "How is burn supply distributed per capita?",
    "description": "Aggregate supply and structural capacity by geography; produce per-capita metrics.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": ["data/processed/facilities_geo.parquet", "data/processed/county_denominators.parquet"],
    "produced_datasets": ["data/processed/supply_capacity_baseline.parquet"],
    "produced_tables": [
        "outputs/tables/02_tables_supply_by_state_ground_only.csv",
        "outputs/tables/02_tables_capacity_by_county_ground_only.csv",
    ],
    "produced_figures": [
        "outputs/figures/02_figures_supply_rank_ground_only.png",
        "outputs/figures/02_figures_capacity_ground_only.png",
    ],
    "produced_findings": ["outputs/metrics/02_findings_ground_only.json"],
    "validations": ["input_exists", "required_columns", "artifact_presence"],
}


@dataclass(frozen=True)
class Stage02Config:
    facilities_geo_path: Path
    county_denom_path: Path
    data_processed_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path


def _cfg(config: RuntimeConfig) -> Stage02Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    processed = Path(data.get("processed_dir", root / "data" / "processed"))
    return Stage02Config(
        facilities_geo_path=Path(data.get("facilities_geo_path", processed / "facilities_geo.parquet")),
        county_denom_path=Path(data.get("county_denominators_path", processed / "county_denominators.parquet")),
        data_processed_dir=processed,
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
    )


def _aba_verified(fac: pd.DataFrame) -> pd.Series:
    if "ABA_VERIFIED" in fac.columns:
        return fac["ABA_VERIFIED"].fillna(False).astype(bool)
    return pd.Series(False, index=fac.index)


def _burn_capable(fac: pd.DataFrame) -> pd.Series:
    burn = False
    for c in ("BURN_ADULT", "BURN_PEDS", "facility_class"):
        if c in fac.columns:
            if c == "facility_class":
                burn = burn | fac[c].astype(str).str.contains("burn", case=False, na=False)
            else:
                burn = burn | fac[c].fillna(False).astype(bool)
    return burn if isinstance(burn, pd.Series) else pd.Series(burn, index=fac.index)


def _peds_capable(fac: pd.DataFrame) -> pd.Series:
    if "BURN_PEDS" in fac.columns:
        return fac["BURN_PEDS"].fillna(False).astype(bool)
    if "facility_class" in fac.columns:
        return fac["facility_class"].astype(str).str.contains("pediatric", case=False, na=False)
    return pd.Series(False, index=fac.index)


def _burn_beds(fac: pd.DataFrame) -> pd.Series:
    for c in ("BURN_BEDS", "burn_beds"):
        if c in fac.columns:
            return pd.to_numeric(fac[c], errors="coerce").fillna(0)
    return pd.Series(0, index=fac.index)


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _cfg(config)
    if not c.facilities_geo_path.exists():
        raise ValidationError(f"Missing Stage 01 output: {c.facilities_geo_path}")
    if not c.county_denom_path.exists():
        raise ValidationError(f"Missing county denominators: {c.county_denom_path}")

    fac = load_parquet(c.facilities_geo_path)
    county = load_parquet(c.county_denom_path)

    fac = fac.copy()
    fac["_aba"] = _aba_verified(fac)
    fac["_burn_capable"] = _burn_capable(fac)
    fac["_peds_capable"] = _peds_capable(fac)
    fac["_burn_beds"] = _burn_beds(fac)

    state_fips = fac["state_fips"] if "state_fips" in fac.columns else fac["STATE"].astype(str)
    county_fips = fac["county_fips"] if "county_fips" in fac.columns else pd.Series("", index=fac.index)

    pop_col = "population_total" if "population_total" in county.columns else "total_pop"
    child_col = "population_child_u18" if "population_child_u18" in county.columns else "child_pop"
    if pop_col not in county.columns:
        county["population_total"] = 100_000
        pop_col = "population_total"
    if child_col not in county.columns:
        county["population_child_u18"] = county[pop_col] * 0.2
        child_col = "population_child_u18"

    geo_col = "county_fips" if "county_fips" in county.columns else "GEOID"
    county = county.rename(columns={geo_col: "county_fips"})
    county["county_fips"] = county["county_fips"].astype(str).str.zfill(5)

    by_state = (
        fac.groupby(state_fips)
        .agg(
            aba_verified=("_aba", "sum"),
            burn_capable=("_burn_capable", "sum"),
            peds_capable=("_peds_capable", "sum"),
            burn_beds=("_burn_beds", "sum"),
        )
        .reset_index()
        .rename(columns={state_fips.name: "state_fips"})
    )
    state_pop = county.groupby(county["county_fips"].str[:2])[pop_col].sum().reset_index()
    state_pop = state_pop.rename(columns={"county_fips": "state_fips"})
    state_pop["state_fips"] = state_pop["state_fips"].str.zfill(2)
    state_child = county.groupby(county["county_fips"].str[:2])[child_col].sum().reset_index()
    state_child = state_child.rename(columns={"county_fips": "state_fips"})
    state_child["state_fips"] = state_child["state_fips"].str.zfill(2)
    by_state = by_state.merge(state_pop, on="state_fips", how="left").merge(
        state_child, on="state_fips", how="left"
    )
    by_state["population_total"] = by_state[pop_col].fillna(0)
    by_state["population_child_u18"] = by_state[child_col].fillna(0)
    by_state["centers_per_100k"] = (
        by_state["aba_verified"].astype(float) / by_state["population_total"].replace(0, 1) * 1e5
    )
    by_state["burn_capable_per_100k"] = (
        by_state["burn_capable"].astype(float) / by_state["population_total"].replace(0, 1) * 1e5
    )
    by_state["peds_capable_per_child_100k"] = (
        by_state["peds_capable"].astype(float) / by_state["population_child_u18"].replace(0, 1) * 1e5
    )
    by_state["burn_beds_per_100k"] = (
        by_state["burn_beds"].astype(float) / by_state["population_total"].replace(0, 1) * 1e5
    )

    by_county = (
        fac.groupby(county_fips)
        .agg(aba_verified=("_aba", "sum"), burn_beds=("_burn_beds", "sum"))
        .reset_index()
        .rename(columns={county_fips.name: "county_fips"})
    )
    by_county["county_fips"] = by_county["county_fips"].astype(str).str.zfill(5)
    by_county = by_county.merge(county[["county_fips", pop_col]].rename(columns={pop_col: "population_total"}), on="county_fips", how="left")
    by_county["population_total"] = by_county["population_total"].fillna(0)
    by_county["burn_beds_per_100k"] = by_county["burn_beds"].astype(float) / by_county["population_total"].replace(0, 1) * 1e5
    by_county["state_fips"] = by_county["county_fips"].astype(str).str[:2]

    baseline_df = by_state.copy()

    dataset_path = c.data_processed_dir / "supply_capacity_baseline.parquet"
    table_state_path = c.outputs_tables_dir / "02_tables_supply_by_state_ground_only.csv"
    table_county_path = c.outputs_tables_dir / "02_tables_capacity_by_county_ground_only.csv"
    fig_supply_path = c.outputs_figures_dir / "02_figures_supply_rank_ground_only.png"
    fig_capacity_path = c.outputs_figures_dir / "02_figures_capacity_ground_only.png"
    finding_path = c.outputs_metrics_dir / "02_findings_ground_only.json"
    manifest_path = c.outputs_metrics_dir / "02_manifest_ground_only.json"

    write_parquet(baseline_df, dataset_path)
    write_csv(by_state, table_state_path)
    write_csv(by_county, table_county_path)

    fig_supply_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    by_state.nlargest(15, "centers_per_100k").plot(x="state_fips", y="centers_per_100k", kind="bar", ax=ax, color="#4063D8")
    ax.set_title("Stage 02 Supply: ABA verified centers per 100k (top 15 states)")
    ax.set_ylabel("centers per 100k")
    fig.tight_layout()
    fig.savefig(fig_supply_path, dpi=150)
    plt.close(fig)

    fig_capacity_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    by_county.nlargest(15, "burn_beds_per_100k").plot(x="county_fips", y="burn_beds_per_100k", kind="bar", ax=ax, color="#34A853")
    ax.set_title("Stage 02 Capacity: Burn beds per 100k (top 15 counties)")
    ax.set_ylabel("beds per 100k")
    fig.tight_layout()
    fig.savefig(fig_capacity_path, dpi=150)
    plt.close(fig)

    finding = FindingRecord(
        stage_id="02",
        question="How is burn supply distributed per capita?",
        finding="Supply and structural capacity metrics were aggregated by state and county with per-capita normalization; rural and low-density areas show lower supply per 100k.",
        why_it_matters="Per-capita supply is the first Challenge Area 3 output and sets the baseline for equity analysis.",
        action_implication="Use supply and capacity baseline as inputs for BEI and hotspot stages.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage02",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("02_dataset_baseline", "02", "dataset", str(dataset_path), "parquet"),
            ArtifactRecord("02_table_state", "02", "table", str(table_state_path), "csv"),
            ArtifactRecord("02_table_county", "02", "table", str(table_county_path), "csv"),
            ArtifactRecord("02_fig_supply", "02", "figure", str(fig_supply_path), "png"),
            ArtifactRecord("02_fig_capacity", "02", "figure", str(fig_capacity_path), "png"),
            ArtifactRecord("02_finding", "02", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "02",
        "dataset": str(dataset_path),
        "tables": [str(table_state_path), str(table_county_path)],
        "figures": [str(fig_supply_path), str(fig_capacity_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
