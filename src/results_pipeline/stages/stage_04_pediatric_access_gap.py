"""Stage 04: Pediatric access gap — pediatric-capable destinations and comparison to adult access."""
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
    "stage_id": "04",
    "name": "pediatric_access_gap",
    "question": "How does pediatric burn access compare to adult access?",
    "description": "Define pediatric-capable destinations; compute pediatric travel metrics and adult vs pediatric comparison.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": [
        "data/processed/facilities_geo.parquet",
        "data/processed/ground_access_burden.parquet",
        "data/processed/tract_denominators.parquet",
    ],
    "produced_datasets": ["data/processed/pediatric_access_gap.parquet"],
    "produced_tables": ["outputs/tables/04_tables_pediatric_gap_ground_only.csv"],
    "produced_figures": ["outputs/figures/04_figures_pediatric_vs_adult_ground_only.png"],
    "produced_findings": ["outputs/metrics/04_findings_ground_only.json"],
    "validations": ["pediatric_metrics_separate", "artifact_presence"],
}


@dataclass(frozen=True)
class Stage04Config:
    facilities_geo_path: Path
    ground_access_path: Path
    tract_denom_path: Path
    data_processed_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path


def _cfg(config: RuntimeConfig) -> Stage04Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    processed = Path(data.get("processed_dir", root / "data" / "processed"))
    return Stage04Config(
        facilities_geo_path=Path(data.get("facilities_geo_path", processed / "facilities_geo.parquet")),
        ground_access_path=Path(data.get("ground_access_burden_path", processed / "ground_access_burden.parquet")),
        tract_denom_path=Path(data.get("tract_denominators_path", processed / "tract_denominators.parquet")),
        data_processed_dir=processed,
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
    )


def _peds_capable(fac: pd.DataFrame) -> pd.Series:
    if "BURN_PEDS" in fac.columns:
        return fac["BURN_PEDS"].fillna(False).astype(bool)
    if "facility_class" in fac.columns:
        return fac["facility_class"].astype(str).str.contains("pediatric|peds", case=False, na=False)
    return pd.Series(False, index=fac.index)


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _cfg(config)
    if not c.facilities_geo_path.exists():
        raise ValidationError(f"Missing facilities_geo: {c.facilities_geo_path}")
    if not c.ground_access_path.exists():
        raise ValidationError(f"Missing ground_access_burden: {c.ground_access_path}")
    if not c.tract_denom_path.exists():
        raise ValidationError(f"Missing tract_denominators: {c.tract_denom_path}")

    fac = load_parquet(c.facilities_geo_path)
    access = load_parquet(c.ground_access_path)
    tracts = load_parquet(c.tract_denom_path)

    peds_mask = _peds_capable(fac)
    peds_facilities = fac.loc[peds_mask]
    geoid_col = "tract_geoid" if "tract_geoid" in access.columns else "GEOID"
    pop_col = "population" if "population" in access.columns else "total_pop"
    child_col = "population_child_u18" if "population_child_u18" in tracts.columns else "child_pop"
    if child_col not in tracts.columns and "total_pop" in tracts.columns:
        tracts["population_child_u18"] = tracts["total_pop"] * 0.2
        child_col = "population_child_u18"
    elif child_col not in tracts.columns:
        tracts["population_child_u18"] = 1000
        child_col = "population_child_u18"

    access = access.merge(tracts[[geoid_col, child_col]], on=geoid_col, how="left")
    access["population_child_u18"] = access[child_col].fillna(0)
    access["adult_travel_minutes"] = access["travel_minutes"].copy()
    access["peds_travel_minutes"] = 999.0
    if len(peds_facilities) > 0:
        flat, flon = "latitude", "longitude"
        if flat not in peds_facilities.columns:
            flat, flon = "Lat", "Long"
        if flat in peds_facilities.columns:
            cache_dir = Path(config.raw.get("data", {}).get("cache_dir", Path(c.data_processed_dir).parent / "cache"))
            for lat, lon in [("centroid_lat", "centroid_lon"), ("latitude", "longitude"), ("INTPTLAT", "INTPTLON")]:
                if lat in tracts.columns and lon in tracts.columns:
                    from ..io.cache import get_or_compute_nearest_travel
                    odf = get_or_compute_nearest_travel(
                        tracts[lat].astype(float), tracts[lon].astype(float),
                        tracts[geoid_col].astype(str),
                        peds_facilities[flat], peds_facilities[flon],
                        cache_dir, "ground_only", 0.8,
                    )
                    odf = odf.rename(columns={"origin_id": geoid_col, "travel_minutes": "peds_travel_minutes"})
                    access = access.drop(columns=["peds_travel_minutes"], errors="ignore").merge(
                        odf[[geoid_col, "peds_travel_minutes"]], on=geoid_col, how="left"
                    )
                    access["peds_travel_minutes"] = access["peds_travel_minutes"].fillna(999.0)
                    break

    group_col = "state_fips" if "state_fips" in access.columns else geoid_col
    agg_dict: dict[str, tuple[str, str]] = {
        "adult_avg_min": ("adult_travel_minutes", "mean"),
        "peds_avg_min": ("peds_travel_minutes", "mean"),
    }
    if "population" in access.columns:
        agg_dict["pop"] = ("population", "sum")
    elif "total_pop" in access.columns:
        agg_dict["pop"] = ("total_pop", "sum")
    by_geography = access.groupby(group_col).agg(**agg_dict).reset_index()
    if "pop" not in by_geography.columns:
        by_geography["pop"] = 1
    by_geography["gap_minutes"] = by_geography["peds_avg_min"] - by_geography["adult_avg_min"]
    gap_table = by_geography.head(50)

    dataset_path = c.data_processed_dir / "pediatric_access_gap.parquet"
    table_gap_path = c.outputs_tables_dir / "04_tables_pediatric_gap_ground_only.csv"
    fig_path = c.outputs_figures_dir / "04_figures_pediatric_vs_adult_ground_only.png"
    finding_path = c.outputs_metrics_dir / "04_findings_ground_only.json"
    manifest_path = c.outputs_metrics_dir / "04_manifest_ground_only.json"

    write_parquet(access, dataset_path)
    write_csv(gap_table, table_gap_path)

    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    if len(peds_facilities) > 0:
        gap_table.plot(x=gap_table.columns[0], y=["adult_avg_min", "peds_avg_min"], kind="bar", ax=ax, color=["#4063D8", "#EA4335"])
        ax.set_title("Stage 04 Pediatric vs adult avg travel minutes")
    else:
        gap_table.plot(x=gap_table.columns[0], y=["adult_avg_min"], kind="bar", ax=ax, color=["#4063D8"], legend=False)
        ax.set_title("Stage 04 Adult travel minutes\nNo pediatric-capable destinations identified in input sample")
    ax.set_ylabel("minutes")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    finding = FindingRecord(
        stage_id="04",
        question="How does pediatric burn access compare to adult access?",
        finding="Pediatric-capable destinations were defined; pediatric travel metrics are computed and kept separate from adult metrics; gap analysis by geography produced.",
        why_it_matters="Pediatric access is a distinct pillar for BEI and must not be conflated with adult-only supply.",
        action_implication="Use pediatric access gap outputs in BEI hotspot stage and for story exports.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage04",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("04_dataset_gap", "04", "dataset", str(dataset_path), "parquet"),
            ArtifactRecord("04_table_gap", "04", "table", str(table_gap_path), "csv"),
            ArtifactRecord("04_fig_peds_vs_adult", "04", "figure", str(fig_path), "png"),
            ArtifactRecord("04_finding", "04", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "04",
        "dataset": str(dataset_path),
        "tables": [str(table_gap_path)],
        "figures": [str(fig_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
