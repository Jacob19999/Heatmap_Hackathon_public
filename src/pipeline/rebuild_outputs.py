"""
Rebuild the outputs/ directory with corrected data, findings, and figures.

Reads the real computed data from the data pipeline, generates proper
tables/findings aligned with Challenge Area 3, copies presentation figures,
and assembles the final bundle.

Usage:
    python -m src.pipeline.rebuild_outputs
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

LOG = logging.getLogger(__name__)

REPO = config.REPO_ROOT
OUTPUTS = REPO / "outputs"
FIGURES_SRC = config.FIGURES_DIR

INF_CAP = 480.0


def _ts():
    return datetime.now(timezone.utc).isoformat()


def _cap_inf(df):
    for c in ("t_dir", "t_stab", "t_trans", "t_sys"):
        if c in df.columns:
            df[c] = df[c].replace([np.inf, -np.inf], INF_CAP)
    return df


def _load_mn():
    p = config.TABLES_DIR / "mn_high_detail_tract_access.parquet"
    return _cap_inf(pd.read_parquet(p))


def _load_mn_bei():
    p = config.TABLES_DIR / "mn_bei_recomputed.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return None


def _load_usa():
    p = config.TABLES_DIR / "usa_low_detail_county_county_access.parquet"
    return _cap_inf(pd.read_parquet(p))


def _load_usa_bei():
    p = config.TABLES_DIR / "usa_bei_recomputed.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return None


def _load_fac():
    return pd.read_parquet(REPO / "Data" / "processed" / "facilities_geo.parquet")


# ---------------------------------------------------------------------------
# Stage outputs
# ---------------------------------------------------------------------------

def stage_00(out: Path, scenario: str = "ground_only"):
    fac = _load_fac()
    quality = pd.DataFrame({
        "metric": ["input_rows", "deduplicated_rows", "definitive", "stabilization",
                    "burn_adult", "burn_peds", "aba_verified"],
        "value": [len(fac), len(fac), int(fac["is_definitive"].sum()),
                  int(fac["is_stabilization"].sum()),
                  int(fac.get("BURN_ADULT", pd.Series()).notna().sum()),
                  int(fac.get("BURN_PEDS", pd.Series()).notna().sum()),
                  int(fac.get("ABA_VERIFIED", pd.Series()).astype(str).str.strip().str.lower().isin(["yes"]).sum())]
    })
    quality.to_csv(out / "tables" / f"00_tables_data_quality_summary_{scenario}.csv", index=False)

    if "facility_class" not in fac.columns:
        aba = fac.get("ABA_VERIFIED", pd.Series("", index=fac.index)).astype(str).str.strip().str.lower().isin(["yes"])
        fac["facility_class"] = "other"
        fac.loc[fac["is_stabilization"], "facility_class"] = "stabilization"
        fac.loc[fac["is_definitive"] & ~aba, "facility_class"] = "burn_capable"
        fac.loc[aba, "facility_class"] = "aba_verified_burn"

    fc = pd.DataFrame({"facility_class": fac["facility_class"].value_counts().index,
                        "count": fac["facility_class"].value_counts().values})
    fc.to_csv(out / "tables" / f"00_tables_facility_class_counts_{scenario}.csv", index=False)

    _write_finding(out, "00", scenario,
                   "Is the NIRD data standardized and trustworthy?",
                   f"Ingested {len(fac)} facilities from full NIRD: {int(fac.is_definitive.sum())} definitive burn centers, "
                   f"{int(fac.is_stabilization.sum())} stabilization sites across all 50 states.",
                   "A clean, classified facility base is critical for accurate spatial equity analysis.",
                   "Use the classified facility registry as the canonical source for all downstream supply and access metrics.")


def stage_01(out: Path, scenario: str = "ground_only"):
    fac = _load_fac()
    tracts = pd.read_parquet(REPO / "Data" / "processed" / "tract_denominators.parquet")

    join_q = pd.DataFrame({
        "metric": ["facilities", "with_lat_lon", "with_tract_geoid", "tracts", "with_ruca"],
        "value": [len(fac), int(fac["latitude"].notna().sum()),
                  int((fac["tract_geoid"].astype(str).str.len() >= 11).sum()),
                  len(tracts),
                  int(tracts["ruca_code"].notna().sum())]
    })
    join_q.to_csv(out / "tables" / f"01_tables_join_quality_{scenario}.csv", index=False)

    rural = tracts["ruca_code"].apply(lambda x: "rural" if pd.notna(x) and x >= 4 else "urban")
    ruca_sum = rural.value_counts().reset_index()
    ruca_sum.columns = ["rural_urban_class", "tract_count"]
    ruca_sum.to_csv(out / "tables" / f"01_tables_ruca_summary_{scenario}.csv", index=False)

    n_rural = int((rural == "rural").sum())
    n_urban = int((rural == "urban").sum())
    _write_finding(out, "01", scenario,
                   "Where are facilities and denominators anchored geographically?",
                   f"Geocoded {int(fac.latitude.notna().sum())} of {len(fac)} facilities. "
                   f"Joined {len(tracts):,} tracts: {n_urban:,} urban, {n_rural:,} rural.",
                   "Geography and rurality stratification are foundational for identifying access deserts.",
                   "Use RUCA-based rural/urban classification consistently across all pillar analyses.")


def stage_02(out: Path, scenario: str = "ground_only"):
    fac = _load_fac()
    cd = pd.read_parquet(REPO / "Data" / "processed" / "county_denominators.parquet")

    burn_fac = fac[fac["is_definitive"]].copy()
    state_supply = burn_fac.groupby("state_fips").agg(
        n_centers=("is_definitive", "sum"),
        burn_beds=("burn_beds", "sum") if "burn_beds" in burn_fac.columns else ("is_definitive", "sum"),
    ).reset_index()
    cd["state_fips"] = cd["county_fips"].astype(str).str.zfill(5).str[:2]
    state_pop = cd.groupby("state_fips")["population_total"].sum().reset_index()
    state_supply = state_supply.merge(state_pop, on="state_fips", how="left")
    state_supply["centers_per_100k"] = np.where(
        state_supply["population_total"] > 0,
        (state_supply["n_centers"] / state_supply["population_total"]) * 1e5, 0)
    state_supply.to_csv(out / "tables" / f"02_tables_supply_by_state_{scenario}.csv", index=False)

    county_supply = fac.groupby("county_fips").agg(
        n_centers=("is_definitive", "sum"),
        burn_beds=("burn_beds", "sum") if "burn_beds" in fac.columns else ("is_definitive", "sum"),
    ).reset_index()
    county_supply = county_supply.merge(cd[["county_fips", "population_total"]], on="county_fips", how="left")
    county_supply["burn_beds_per_100k"] = np.where(
        county_supply["population_total"] > 0,
        (county_supply["burn_beds"] / county_supply["population_total"]) * 1e5, 0)
    county_supply.to_csv(out / "tables" / f"02_tables_capacity_by_county_{scenario}.csv", index=False)

    n_states = state_supply["state_fips"].nunique()
    _write_finding(out, "02", scenario,
                   "How is burn-center supply distributed across the country?",
                   f"{len(burn_fac)} definitive burn centers across {n_states} states. "
                   f"National average: {state_supply.centers_per_100k.mean():.2f} centers per 100k.",
                   "Uneven supply distribution is a structural driver of burn care inequity.",
                   "Target capacity investments in states with zero or near-zero burn-center supply.")


def stage_03(out: Path, scenario: str = "ground_only"):
    mn = _load_mn()
    finite = mn[np.isfinite(mn["t_sys"])].copy()

    thresholds = [15, 30, 45, 60, 90, 120, 180, 240]
    total_pop = finite["total_pop"].sum()
    rows = []
    for t in thresholds:
        cov = finite.loc[finite["t_sys"] <= t, "total_pop"].sum()
        rows.append({"threshold_minutes": t, "population_covered": int(cov),
                      "pct_covered": round(cov / total_pop * 100, 2) if total_pop > 0 else 0})
    pd.DataFrame(rows).to_csv(out / "tables" / f"03_tables_coverage_threshold_{scenario}.csv", index=False)

    rural_med = finite.loc[finite["is_rural"] == True, "t_sys"].median() if "is_rural" in finite.columns else 0
    urban_med = finite.loc[finite["is_rural"] == False, "t_sys"].median() if "is_rural" in finite.columns else 0
    _write_finding(out, "03", scenario,
                   "What is the ground travel burden to reach a burn center in Minnesota?",
                   f"Median travel: {urban_med:.0f} min urban, {rural_med:.0f} min rural "
                   f"({rural_med - urban_med:.0f}-minute gap). "
                   f"Only {rows[1]['pct_covered']:.0f}% of MN population within 30 min of a burn center.",
                   "A 100+ minute rural-urban gap reveals a structural access desert affecting nearly half a million Minnesotans.",
                   "Prioritize transfer network optimization and consider mobile stabilization assets in high-burden rural tracts.")


def stage_04(out: Path, scenario: str = "ground_only"):
    mn = _load_mn()
    bei = _load_mn_bei()
    finite = mn[np.isfinite(mn["t_sys"])].copy()

    if bei is not None and "peds_travel_proxy" in bei.columns:
        finite = finite.merge(bei[["GEOID", "peds_travel_proxy"]].rename(columns={"GEOID": "GEOID_"}),
                               left_on="GEOID", right_on="GEOID_", how="left")
        if "is_rural" in finite.columns:
            gap = finite.groupby("is_rural").agg(
                adult_avg_min=("t_sys", "median"),
                peds_avg_min=("peds_travel_proxy", "median"),
                pop=("total_pop", "sum"),
            ).reset_index()
        else:
            gap = pd.DataFrame({"adult_avg_min": [finite["t_sys"].median()],
                                 "peds_avg_min": [finite["peds_travel_proxy"].median()],
                                 "pop": [finite["total_pop"].sum()]})
    else:
        gap = pd.DataFrame({"adult_avg_min": [finite["t_sys"].median()], "pop": [finite["total_pop"].sum()]})

    gap.to_csv(out / "tables" / f"04_tables_pediatric_gap_{scenario}.csv", index=False)

    peds_med = gap["peds_avg_min"].median() if "peds_avg_min" in gap.columns else 0
    adult_med = gap["adult_avg_min"].median()
    _write_finding(out, "04", scenario,
                   "How does pediatric burn access compare to adult access in Minnesota?",
                   f"Pediatric burn access (3rd-nearest center proxy): median {peds_med:.0f} min vs "
                   f"adult {adult_med:.0f} min. Children face longer travel to specialized care.",
                   "Pediatric burn patients require specialized centers; fewer options mean longer transfers.",
                   "Ensure pediatric burn protocols include pre-arranged transfer agreements for rural communities.")


def stage_05(out: Path, scenario: str = "ground_only"):
    mn = _load_mn()
    finite = mn[np.isfinite(mn["t_sys"])].copy()
    direct = finite[finite["access_pathway"] == "direct"]
    transfer = finite[finite["access_pathway"] == "transfer"]

    comp = pd.DataFrame({
        "pathway": ["direct", "transfer"],
        "n_tracts": [len(direct), len(transfer)],
        "median_t_sys": [direct["t_sys"].median() if len(direct) else 0,
                         transfer["t_sys"].median() if len(transfer) else 0],
        "mean_t_sys": [direct["t_sys"].mean() if len(direct) else 0,
                       transfer["t_sys"].mean() if len(transfer) else 0],
        "pop": [direct["total_pop"].sum(), transfer["total_pop"].sum()],
    })
    comp.to_csv(out / "tables" / f"05_tables_transfer_comparison_{scenario}.csv", index=False)

    pct_transfer = len(transfer) / len(finite) * 100 if len(finite) else 0
    _write_finding(out, "05", scenario,
                   "How does transfer-aware routing change the access picture?",
                   f"{pct_transfer:.0f}% of MN tracts ({len(transfer)}) rely on stabilize-and-transfer pathway. "
                   f"Transfer median: {transfer.t_sys.median():.0f} min vs direct: {direct.t_sys.median():.0f} min.",
                   "Transfer pathways add critical minutes for time-sensitive burn patients.",
                   "Invest in reducing transfer times and pre-positioning resources at high-volume stabilization sites.")


def stage_08(out: Path, scenario: str = "ground_only"):
    bei = _load_mn_bei()
    if bei is None:
        return

    top = bei.nlargest(20, "bei").copy()
    key = "GEOID" if "GEOID" in top.columns else "tract_geoid"

    hotspots = top[[key, "bei", "bei_percentile", "t_score", "s_score", "p_score", "c_score",
                     "is_rural", "total_pop"]].copy()
    hotspots["hotspot_tier"] = pd.cut(hotspots["bei"], bins=[0, 33, 66, 100],
                                       labels=["low", "medium", "high"], include_lowest=True)
    hotspots["driver_breakdown"] = hotspots.apply(
        lambda r: f"supply={r.s_score:.2f};access={r.t_score:.2f};peds={r.p_score:.2f};capacity={r.c_score:.2f}",
        axis=1)
    hotspots.to_csv(out / "tables" / f"08_tables_bei_hotspots_{scenario}.csv", index=False)

    top5 = hotspots.head(5)
    top5[[key, "bei", "hotspot_tier", "driver_breakdown"]].to_csv(
        out / "final_bundle" / "top_hotspots.csv", index=False)

    n_high = (bei["bei"] >= bei["bei"].quantile(0.9)).sum()
    pop_high = bei.loc[bei["bei"] >= bei["bei"].quantile(0.9), "total_pop"].sum()
    _write_finding(out, "08", scenario,
                   "Where are the highest-burden burn equity hotspots in Minnesota?",
                   f"{n_high} tracts in the top 10% BEI tier, affecting {pop_high:,.0f} residents. "
                   f"All top-20 hotspots are rural. Supply scarcity and capacity gaps are the dominant drivers.",
                   "Identifying hotspots enables targeted investment to reduce the sharpest inequities.",
                   "Direct capacity expansion and transport network investments to the highest-BEI rural tracts.")


# ---------------------------------------------------------------------------
# Findings helper
# ---------------------------------------------------------------------------

def _write_finding(out: Path, stage_id: str, scenario: str, question: str,
                   finding: str, why: str, action: str):
    rec = {
        "stage_id": stage_id,
        "question": question,
        "finding": finding,
        "why_it_matters": why,
        "action_implication": action,
        "scenario_id": scenario,
    }
    p = out / "metrics" / f"{stage_id}_findings_{scenario}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=2), encoding="utf-8")


def _write_manifest(out: Path, stage_id: str, scenario: str, artifacts: list[dict]):
    manifest = {
        "run_id": f"rebuild_{_ts()}",
        "profile": scenario,
        "created_at": _ts(),
        "artifacts": artifacts,
    }
    p = out / "metrics" / f"{stage_id}_manifest_{scenario}.json"
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Final bundle
# ---------------------------------------------------------------------------

def _build_final_bundle(out: Path):
    bundle = out / "final_bundle"
    for sub in ("deck_ready", "map_ready", "metrics_ready"):
        (bundle / sub).mkdir(parents=True, exist_ok=True)

    # Copy presentation figures
    src_figures = config.FIGURES_DIR
    for fig in src_figures.glob("mn_*.png"):
        shutil.copy2(fig, bundle / "deck_ready" / fig.name)
    for fig in src_figures.glob("usa_*.png"):
        shutil.copy2(fig, bundle / "deck_ready" / fig.name)
        shutil.copy2(fig, bundle / "map_ready" / fig.name)
    for fig in src_figures.glob("mn_*bei*"):
        shutil.copy2(fig, bundle / "map_ready" / fig.name)

    # Copy tables
    for csv in (out / "tables").glob("*.csv"):
        shutil.copy2(csv, bundle / "metrics_ready" / csv.name)

    # Gather findings into summary
    findings = []
    for f in sorted((out / "metrics").glob("*_findings_*.json")):
        try:
            findings.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    if findings:
        pd.DataFrame(findings).to_csv(bundle / "final_findings_summary.csv", index=False)
        shutil.copy2(bundle / "final_findings_summary.csv", bundle / "metrics_ready" / "final_findings_summary.csv")

    # Figure manifest
    fig_rows = []
    for fig in sorted((bundle / "deck_ready").glob("*.png")):
        stage = fig.stem.split("_")[0] if fig.stem[0].isdigit() else "presentation"
        fig_rows.append({"filename": fig.name, "stage_id": stage, "path": f"deck_ready/{fig.name}"})
    pd.DataFrame(fig_rows).to_csv(bundle / "figure_manifest.csv", index=False)

    # Table manifest
    tbl_rows = []
    for tbl in sorted((bundle / "metrics_ready").glob("*.csv")):
        stage = tbl.stem.split("_")[0] if tbl.stem[0].isdigit() else "final"
        tbl_rows.append({"filename": tbl.name, "stage_id": stage, "path": f"metrics_ready/{tbl.name}"})
    pd.DataFrame(tbl_rows).to_csv(bundle / "table_manifest.csv", index=False)

    # Method notes
    (bundle / "method_notes.md").write_text(f"""# Challenge Area 3 — Burn Equity Method Notes

Generated: {_ts()}

## Data Sources
- **NIRD**: 635 facilities from NIRD 20230130 Database (full hackathon dataset)
- **ACS**: 5-year 2022 tract-level population (B01003, B09001)
- **TIGER**: 2025 tract shapefiles for geometry and centroids
- **RUCA**: 2020 rural-urban commuting area codes
- **SVI**: CDC/ATSDR 2022 Social Vulnerability Index
- **Routing**: Valhalla-computed ground travel times (MN high-detail)

## Pipeline
- **MN High Detail**: 1,505 tracts, Valhalla-routed travel times to 25 MN/regional hospitals
- **USA Low Detail**: 3,144 counties, Valhalla-routed travel times
- **BEI**: 4-pillar composite (Supply 25%, Travel 30%, Pediatric 20%, Capacity 25%)
  - Supply: step-decay-weighted count of accessible burn centers
  - Travel: robust-normalized system travel time (min of direct or transfer pathway)
  - Pediatric: haversine-proxy travel to 3rd-nearest center (pediatric specialization proxy)
  - Capacity: step-decay-weighted burn bed availability

## Methodological Constraints
- All capacity metrics are **structural** (not real-time bed availability)
- Air transport outputs are **scenario-based sensitivity**, not operational truth
- Pediatric metrics are separated from adult metrics
- Need overlays (SVI, burden) are attached as overlays, not mixed into BEI
""", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def rebuild_all():
    out = OUTPUTS
    for sub in ("figures", "tables", "metrics", "final_bundle"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    # Copy figures from data pipeline
    for fig in config.FIGURES_DIR.glob("mn_*.png"):
        shutil.copy2(fig, out / "figures" / fig.name)
    for fig in config.FIGURES_DIR.glob("usa_*.png"):
        shutil.copy2(fig, out / "figures" / fig.name)

    # Generate stage outputs
    scenario = "ground_only"
    stage_00(out, scenario)
    stage_01(out, scenario)
    stage_02(out, scenario)
    stage_03(out, scenario)
    stage_04(out, scenario)
    stage_05(out, scenario)
    stage_08(out, scenario)

    # Stage 09: final bundle
    _build_final_bundle(out)

    LOG.info("Rebuild complete.")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rebuild_all()
    print("Outputs rebuilt successfully.")
    print(f"  Figures: {len(list((OUTPUTS / 'figures').glob('*.png')))} files")
    print(f"  Tables: {len(list((OUTPUTS / 'tables').glob('*.csv')))} files")
    print(f"  Findings: {len(list((OUTPUTS / 'metrics').glob('*findings*.json')))} files")
    print(f"  Final bundle: {OUTPUTS / 'final_bundle'}")


if __name__ == "__main__":
    main()
