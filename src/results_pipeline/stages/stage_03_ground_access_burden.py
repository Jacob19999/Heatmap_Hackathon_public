"""Stage 03: Ground access burden — travel time to nearest burn/verified facility."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from ..contracts.artifacts import ArtifactManifest, ArtifactRecord, FindingRecord
from ..io.cache import get_or_compute_nearest_travel
from ..io.loaders import load_parquet
from ..io.writers import write_csv, write_finding, write_manifest, write_parquet
from ..settings import RuntimeConfig
from ..utils.validation import ValidationError

STAGE_META: dict[str, Any] = {
    "stage_id": "03",
    "name": "ground_access_burden",
    "question": "What is the ground travel burden to reach burn care?",
    "description": "Estimate travel time to nearest verified/burn-capable facility; summarize by tract, county, state, RUCA.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": ["data/processed/facilities_geo.parquet", "data/processed/tract_denominators.parquet"],
    "produced_datasets": ["data/processed/ground_access_burden.parquet"],
    "produced_tables": ["outputs/tables/03_tables_coverage_threshold_ground_only.csv"],
    "produced_figures": ["outputs/figures/03_figures_rural_urban_burden_ground_only.png"],
    "produced_findings": ["outputs/metrics/03_findings_ground_only.json"],
    "validations": ["input_exists", "routing_or_cache", "artifact_presence"],
}


@dataclass(frozen=True)
class Stage03Config:
    facilities_geo_path: Path
    tract_denom_path: Path
    county_denom_path: Path | None
    data_processed_dir: Path
    cache_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path
    km_per_minute: float


def _cfg(config: RuntimeConfig) -> Stage03Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    processed = Path(data.get("processed_dir", root / "data" / "processed"))
    return Stage03Config(
        facilities_geo_path=Path(data.get("facilities_geo_path", processed / "facilities_geo.parquet")),
        tract_denom_path=Path(data.get("tract_denominators_path", processed / "tract_denominators.parquet")),
        county_denom_path=Path(data.get("county_denominators_path", processed / "county_denominators.parquet")) if data.get("county_denominators_path") else None,
        data_processed_dir=processed,
        cache_dir=Path(data.get("cache_dir", root / "data" / "cache")),
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
        km_per_minute=float(config.raw.get("routing", {}).get("km_per_minute", 0.8)),
    )


def _burn_capable(fac: pd.DataFrame) -> pd.Series:
    burn = pd.Series(False, index=fac.index)
    for c in ("BURN_ADULT", "BURN_PEDS", "facility_class", "ABA_VERIFIED"):
        if c in fac.columns:
            if c == "facility_class":
                burn = burn | fac[c].astype(str).str.contains("burn", case=False, na=False)
            else:
                burn = burn | fac[c].fillna(False).astype(bool)
    return burn


def _lat_lon_columns(df: pd.DataFrame) -> tuple[str, str]:
    """
    Return a pair of latitude/longitude column names for a dataframe.
    """
    for lat, lon in [
        ("centroid_lat", "centroid_lon"),
        ("latitude", "longitude"),
        ("Lat", "Long"),
        ("INTPTLAT", "INTPTLON"),
    ]:
        if lat in df.columns and lon in df.columns:
            return lat, lon
    raise ValidationError(
        "Missing coordinate columns. Expected one of centroid_lat/centroid_lon, "
        "latitude/longitude, Lat/Long, or INTPTLAT/INTPTLON."
    )


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _cfg(config)
    if not c.facilities_geo_path.exists():
        raise ValidationError(f"Missing facilities_geo: {c.facilities_geo_path}")
    if not c.tract_denom_path.exists():
        raise ValidationError(f"Missing tract denominators: {c.tract_denom_path}")

    fac = load_parquet(c.facilities_geo_path)
    tracts = load_parquet(c.tract_denom_path)

    dest_mask = _burn_capable(fac)
    if dest_mask.sum() == 0:
        dest_mask = pd.Series(True, index=fac.index)
    facilities = fac.loc[dest_mask].copy()
    flat, flon = _lat_lon_columns(facilities)
    facilities_lat = facilities[flat]
    facilities_lon = facilities[flon]

    olat, olon = _lat_lon_columns(tracts)
    origin_lat = tracts[olat].astype(float)
    origin_lon = tracts[olon].astype(float)
    geoid_col = "tract_geoid" if "tract_geoid" in tracts.columns else "GEOID"
    origin_ids = tracts[geoid_col].astype(str)

    travel_df = get_or_compute_nearest_travel(
        origin_lat, origin_lon, origin_ids,
        facilities_lat, facilities_lon,
        c.cache_dir, scenario_id="ground_only", km_per_minute=c.km_per_minute,
    )
    travel_df = travel_df.rename(columns={"origin_id": geoid_col})
    tracts = tracts.merge(travel_df, on=geoid_col, how="left")
    tracts["travel_minutes"] = tracts["travel_minutes"].fillna(999)

    pop_col = "total_pop" if "total_pop" in tracts.columns else "population_total"
    if pop_col not in tracts.columns:
        tracts[pop_col] = 1000
    tracts["state_fips"] = tracts[geoid_col].astype(str).str[:2]
    tracts["county_fips"] = tracts[geoid_col].astype(str).str[:5]

    by_tract = tracts[[geoid_col, "state_fips", "county_fips", "travel_minutes", pop_col]].copy()
    by_tract = by_tract.rename(columns={geoid_col: "tract_geoid"})

    tracts = tracts.copy()
    tracts["_pop_weight"] = tracts[pop_col].fillna(0).astype(float).replace(0, 1.0)
    tracts["_travel_weighted"] = tracts["travel_minutes"] * tracts["_pop_weight"]

    by_county = (
        tracts.groupby("county_fips", dropna=False)[["_travel_weighted", "_pop_weight", pop_col]]
        .sum()
        .reset_index()
    )
    by_county["avg_travel_minutes"] = by_county["_travel_weighted"] / by_county["_pop_weight"]
    by_county = by_county[["county_fips", "avg_travel_minutes", pop_col]]

    by_state = (
        tracts.groupby("state_fips", dropna=False)[["_travel_weighted", "_pop_weight", pop_col]]
        .sum()
        .reset_index()
    )
    by_state["avg_travel_minutes"] = by_state["_travel_weighted"] / by_state["_pop_weight"]
    by_state = by_state[["state_fips", "avg_travel_minutes", pop_col]]

    ruca_col = "ruca_code" if "ruca_code" in tracts.columns else "RUCA"
    if ruca_col in tracts.columns:
        by_ruca = (
            tracts.groupby(ruca_col, dropna=False)[["_travel_weighted", "_pop_weight"]]
            .sum()
            .reset_index()
        )
        by_ruca["avg_travel_minutes"] = by_ruca["_travel_weighted"] / by_ruca["_pop_weight"]
        by_ruca = by_ruca[[ruca_col, "avg_travel_minutes"]]
    else:
        by_ruca = pd.DataFrame(columns=["ruca_code", "avg_travel_minutes"])

    thresholds = [15, 30, 45, 60, 90, 120]
    coverage_rows = []
    for thresh in thresholds:
        p = tracts.loc[tracts["travel_minutes"] <= thresh, pop_col].sum()
        total = tracts[pop_col].sum()
        pct = 100 * p / total if total else 0
        coverage_rows.append({"threshold_minutes": thresh, "population_covered": int(p), "pct_covered": round(pct, 2)})
    coverage_table = pd.DataFrame(coverage_rows)

    dataset_path = c.data_processed_dir / "ground_access_burden.parquet"
    table_coverage_path = c.outputs_tables_dir / "03_tables_coverage_threshold_ground_only.csv"
    fig_burden_path = c.outputs_figures_dir / "03_figures_rural_urban_burden_ground_only.png"
    finding_path = c.outputs_metrics_dir / "03_findings_ground_only.json"
    manifest_path = c.outputs_metrics_dir / "03_manifest_ground_only.json"

    write_parquet(by_tract, dataset_path)
    write_csv(coverage_table, table_coverage_path)

    fig_burden_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    if by_ruca.shape[0] > 0:
        by_ruca.plot(x=by_ruca.columns[0], y="avg_travel_minutes", kind="bar", ax=ax, color="#EA4335", legend=False)
        ax.set_title("Stage 03 Ground access: avg travel minutes by RUCA")
    else:
        by_state.nlargest(15, "avg_travel_minutes").plot(x="state_fips", y="avg_travel_minutes", kind="bar", ax=ax, color="#EA4335", legend=False)
        ax.set_title("Stage 03 Ground access: avg travel minutes (top 15 states)")
    ax.set_ylabel("minutes")
    fig.tight_layout()
    fig.savefig(fig_burden_path, dpi=150)
    plt.close(fig)

    finding = FindingRecord(
        stage_id="03",
        question="What is the ground travel burden to reach burn care?",
        finding="Travel time to nearest burn-capable facility was estimated; coverage thresholds and rural/urban summaries produced.",
        why_it_matters="Ground access is a core equity metric for Challenge Area 3.",
        action_implication="Use ground access metrics in BEI and for pediatric/transfer comparisons.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage03",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("03_dataset_burden", "03", "dataset", str(dataset_path), "parquet"),
            ArtifactRecord("03_table_coverage", "03", "table", str(table_coverage_path), "csv"),
            ArtifactRecord("03_fig_burden", "03", "figure", str(fig_burden_path), "png"),
            ArtifactRecord("03_finding", "03", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "03",
        "dataset": str(dataset_path),
        "tables": [str(table_coverage_path)],
        "figures": [str(fig_burden_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
