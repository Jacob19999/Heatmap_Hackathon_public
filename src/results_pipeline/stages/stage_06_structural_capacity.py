"""Stage 06: Structural capacity competition — catchments and accessibility (structural only, not real-time)."""
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
    "stage_id": "06",
    "name": "structural_capacity",
    "question": "Where is structural capacity competition highest?",
    "description": "Build structural catchments and accessibility/competition scores; outputs are structural only, not real-time bed availability.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": [
        "data/processed/facilities_geo.parquet",
        "data/processed/supply_capacity_baseline.parquet",
        "data/processed/county_denominators.parquet",
    ],
    "produced_datasets": ["data/processed/structural_capacity.parquet"],
    "produced_tables": ["outputs/tables/06_tables_structural_competition_ground_only.csv"],
    "produced_figures": ["outputs/figures/06_figures_structural_competition_ground_only.png"],
    "produced_findings": ["outputs/metrics/06_findings_ground_only.json"],
    "validations": ["structural_not_realtime", "artifact_presence"],
}


@dataclass(frozen=True)
class Stage06Config:
    facilities_geo_path: Path
    supply_baseline_path: Path
    county_denom_path: Path
    data_processed_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path


def _cfg(config: RuntimeConfig) -> Stage06Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    processed = Path(data.get("processed_dir", root / "data" / "processed"))
    return Stage06Config(
        facilities_geo_path=Path(data.get("facilities_geo_path", processed / "facilities_geo.parquet")),
        supply_baseline_path=Path(data.get("supply_baseline_path", processed / "supply_capacity_baseline.parquet")),
        county_denom_path=Path(data.get("county_denominators_path", processed / "county_denominators.parquet")),
        data_processed_dir=processed,
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
    )


def _burn_beds(fac: pd.DataFrame) -> pd.Series:
    for col in ("BURN_BEDS", "burn_beds"):
        if col in fac.columns:
            return pd.to_numeric(fac[col], errors="coerce").fillna(0)
    return pd.Series(0, index=fac.index)


def run(config: RuntimeConfig) -> dict[str, Any]:
    sc = _cfg(config)
    if not sc.facilities_geo_path.exists():
        raise ValidationError(f"Missing facilities_geo: {sc.facilities_geo_path}")
    if not sc.supply_baseline_path.exists():
        raise ValidationError(f"Missing supply_capacity_baseline: {sc.supply_baseline_path}")
    if not sc.county_denom_path.exists():
        raise ValidationError(f"Missing county_denominators: {sc.county_denom_path}")

    fac = load_parquet(sc.facilities_geo_path)
    supply = load_parquet(sc.supply_baseline_path)
    county = load_parquet(sc.county_denom_path)

    county_fips = "county_fips" if "county_fips" in fac.columns else "COUNTY_FIPS"
    if county_fips not in fac.columns:
        county_fips = county.columns[0] if "county_fips" in county.columns else "GEOID"
    fac = fac.copy()
    fac["_burn_beds"] = _burn_beds(fac)
    if county_fips not in fac.columns:
        fac["county_fips"] = ""
    else:
        fac["county_fips"] = fac[county_fips].astype(str).str.zfill(5)

    geo_col = "county_fips" if "county_fips" in county.columns else "GEOID"
    county = county.copy()
    county["county_fips"] = county[geo_col].astype(str).str.zfill(5)
    pop_col = "population_total" if "population_total" in county.columns else "total_pop"
    if pop_col not in county.columns:
        for c in county.columns:
            if "pop" in c.lower():
                pop_col = c
                break
        else:
            pop_col = county.columns[1] if len(county.columns) > 1 else county.columns[0]
    county["population_total"] = pd.to_numeric(county[pop_col], errors="coerce").fillna(0)

    by_county = (
        fac.groupby("county_fips")
        .agg(facility_count=("_burn_beds", "count"), burn_beds=("_burn_beds", "sum"))
        .reset_index()
    )
    by_county = by_county.merge(
        county[["county_fips", "population_total"]],
        on="county_fips",
        how="left",
    )
    by_county["population_total"] = by_county["population_total"].fillna(0).replace(0, 1)
    by_county["structural_competition_per_bed"] = by_county["population_total"] / by_county["burn_beds"].replace(0, 1)
    by_county["structural_competition_per_facility"] = by_county["population_total"] / by_county["facility_count"].replace(0, 1)
    by_county["beds_per_100k"] = by_county["burn_beds"] / by_county["population_total"] * 1e5
    by_county["capacity_type"] = "structural"
    by_county["not_realtime"] = True

    dataset_path = sc.data_processed_dir / "structural_capacity.parquet"
    table_path = sc.outputs_tables_dir / "06_tables_structural_competition_ground_only.csv"
    fig_path = sc.outputs_figures_dir / "06_figures_structural_competition_ground_only.png"
    finding_path = sc.outputs_metrics_dir / "06_findings_ground_only.json"
    manifest_path = sc.outputs_metrics_dir / "06_manifest_ground_only.json"

    write_parquet(by_county, dataset_path)
    write_csv(by_county, table_path)

    fig, ax = plt.subplots(figsize=(8, 4))
    top = by_county.nlargest(15, "structural_competition_per_bed")
    top.plot(x="county_fips", y="structural_competition_per_bed", kind="bar", ax=ax, color="#FBBC04", legend=False)
    ax.set_title("Stage 06 Structural capacity competition (pop per bed, top 15 counties)\nStructural only — not real-time availability")
    ax.set_ylabel("population per burn bed")
    fig.tight_layout()
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    finding = FindingRecord(
        stage_id="06",
        question="Where is structural capacity competition highest?",
        finding="Structural catchments and competition scores were computed by county; metrics reflect infrastructure capacity only and do not represent real-time bed availability.",
        why_it_matters="Structural competition identifies areas where demand for burn care infrastructure is high relative to installed capacity.",
        action_implication="Use structural capacity outputs for BEI when running full profile; do not interpret as real-time occupancy.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage06",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("06_dataset_structural", "06", "dataset", str(dataset_path), "parquet"),
            ArtifactRecord("06_table_competition", "06", "table", str(table_path), "csv"),
            ArtifactRecord("06_fig_competition", "06", "figure", str(fig_path), "png"),
            ArtifactRecord("06_finding", "06", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "06",
        "dataset": str(dataset_path),
        "tables": [str(table_path)],
        "figures": [str(fig_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
