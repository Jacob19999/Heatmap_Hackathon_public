"""Minnesota high-detail pipeline using the dataset-profile abstraction.

This module runs the downstream access + BEI steps for Minnesota tracts only,
using national ingestion/routing inputs but exporting profile-scoped outputs
for the `mn_high_detail` presentation profile (and its legacy `mn_mvp` alias).
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .access import compute_access_times
from .bei_components import robust_norm
from .bei_composite import compute_composite_bei
from .presentation_scope import DatasetProfile, get_profile
from .export import scoped_tables_dir, write_presentation_manifest, get_profile_assets
from .routing_inputs import build_inputs
from .routing import compute_travel_time_matrix

LOG = logging.getLogger(__name__)

MN_STATE_FIPS = "27"


def _regional_state_abbrs(profile: DatasetProfile) -> set[str]:
    return {abbr.upper() for abbr in profile.destination_state_filter}


def _regional_state_fips(profile: DatasetProfile) -> set[str]:
    return {s.zfill(2) for s in profile.origin_state_fips} | {
        # allow destination state filters that are already FIPS-like
        s.zfill(2)
        for s in profile.destination_state_filter
        if s.isdigit()
    }


def _mn_paths(profile: DatasetProfile) -> dict[str, Path]:
    """Return canonical paths for the MN matrix and derived outputs."""
    tables = scoped_tables_dir(profile)
    base = Path(profile.matrix_raw_path)
    filled = Path(profile.matrix_filled_path)
    prefix = profile.output_prefix
    paths = {
        "matrix_raw": base,
        "matrix_filled": filled,
        "tract_access": tables / f"{prefix}_tract_access.parquet",
        "tract_bei": tables / f"{prefix}_tract_bei.parquet",
    }
    # Backwards-compatibility: if the new-profile filenames are missing but
    # legacy `mn_mvp_*` outputs exist, point to those so we can reuse them
    # without recomputing for the MN presentation build.
    legacy_prefix = "mn_mvp"
    legacy_access = tables / f"{legacy_prefix}_tract_access.parquet"
    legacy_bei = tables / f"{legacy_prefix}_tract_bei.parquet"
    if not paths["tract_access"].exists() and legacy_access.exists():
        paths["tract_access"] = legacy_access
    if not paths["tract_bei"].exists() and legacy_bei.exists():
        paths["tract_bei"] = legacy_bei
    return paths


def _load_mn_matrix(profile: DatasetProfile) -> pd.DataFrame:
    """Load the MN travel-time matrix, computing it via routing API if missing.

    Prefers the filled version when present. If neither the raw nor filled
    parquet exists, a Minnesota/regional matrix is computed on the fly using
    Valhalla / the configured routing engine and saved to the canonical path.
    """
    paths = _mn_paths(profile)
    if not (paths["matrix_filled"].exists() or paths["matrix_raw"].exists()):
        LOG.info(
            "MN travel-time matrix not found on disk; computing Minnesota/regional "
            "matrix via routing API and saving to %s",
            paths["matrix_raw"],
        )
        # Build Minnesota tracts and regional hospitals for routing.
        tracts_all, facilities_all = build_inputs()
        tracts_mn, facilities_regional = _subset_mn(tracts_all, facilities_all, profile)
        LOG.info(
            "Routing inputs for MN matrix: %d MN tracts × %d regional hospitals.",
            len(tracts_mn),
            len(facilities_regional),
        )
        origins = tracts_mn.rename(columns={"GEOID": "tract_geoid"})
        destinations = facilities_regional
        # Use a conservative Valhalla configuration similar to the national run.
        compute_travel_time_matrix(
            origins=origins,
            destinations=destinations,
            origin_id_col="tract_geoid",
            dest_id_col="AHA_ID",
            out_path=paths["matrix_raw"],
            routing_engine="valhalla",
            batch_size=15,
            max_workers=1,
            prefilter=True,
            max_haversine_km=150.0,
            min_k=3,
            return_df=False,
        )

    if paths["matrix_filled"].exists():
        path = paths["matrix_filled"]
    else:
        path = paths["matrix_raw"]
    LOG.info("Loading MN matrix from %s", path)
    df = pd.read_parquet(path).copy()
    # Handle both raw and filled schema: prefer duration_min_filled when available.
    if "duration_min_filled" in df.columns:
        df["duration_min"] = df["duration_min_filled"]
    if not {"origin_id", "destination_id", "duration_min"}.issubset(df.columns):
        missing = {"origin_id", "destination_id", "duration_min"} - set(df.columns)
        raise ValueError(f"MN matrix is missing required columns: {sorted(missing)}")
    # Normalize id types to string to match build_inputs outputs.
    df["origin_id"] = df["origin_id"].astype(str)
    df["destination_id"] = df["destination_id"].astype(str)
    return df


def _subset_mn(
    tracts: pd.DataFrame,
    facilities: pd.DataFrame,
    profile: DatasetProfile,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restrict inputs to MN tracts and hospitals in MN plus nearby states."""
    tr_mn = tracts[tracts["GEOID"].astype(str).str[:2] == MN_STATE_FIPS].copy()
    # Facilities: keep Minnesota plus adjacent-state hospitals so Minnesota
    # residents near the border can route to nearby cross-state options.
    fac = facilities.copy()
    regional_abbrs = _regional_state_abbrs(profile)
    regional_fips = _regional_state_fips(profile)
    if "STATE" in fac.columns:
        in_region_abbr = fac["STATE"].astype(str).str.upper().isin(regional_abbrs)
    else:
        in_region_abbr = pd.Series(False, index=fac.index)
    if "state_fips" in fac.columns:
        in_region_fips = fac["state_fips"].astype(str).str.zfill(2).isin(regional_fips)
    else:
        in_region_fips = pd.Series(False, index=fac.index)
    fac_mn = fac[in_region_abbr | in_region_fips].copy()
    return tr_mn, fac_mn


def run_mn_pipeline(profile_id: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the MN high-detail pipeline end-to-end and return (mn_access, mn_bei).

    The dataset profile controls matrix paths, output prefixes, and regional
    destination filtering. By default this uses the default profile configured
    in `config.DEFAULT_PROFILE_ID` (currently `mn_high_detail`).
    """
    profile = get_profile(profile_id)
    paths = _mn_paths(profile)

    # Fast path: if tract-level MN access + BEI tables already exist on disk,
    # reuse them directly instead of recomputing heavy routing/analytics.
    if paths["tract_access"].exists() and paths["tract_bei"].exists():
        LOG.info(
            "Reusing existing MN high-detail outputs from %s and %s",
            paths["tract_access"],
            paths["tract_bei"],
        )
        access_mn = pd.read_parquet(paths["tract_access"])
        mn_bei = pd.read_parquet(paths["tract_bei"])
        return access_mn, mn_bei
    LOG.info("Building canonical inputs (tracts + facilities) ...")
    tracts_all, facilities_all = build_inputs()
    LOG.info("Loaded %d tracts and %d facilities (nationwide).", len(tracts_all), len(facilities_all))

    LOG.info("Subsetting to Minnesota tracts and regional hospitals ...")
    tracts_mn, facilities_mn = _subset_mn(tracts_all, facilities_all, profile)
    LOG.info(
        "%s subset: %d tracts, %d facilities.",
        profile.display_name,
        len(tracts_mn),
        len(facilities_mn),
    )

    LOG.info("Loading MN travel-time matrix ...")
    matrix_mn = _load_mn_matrix(profile)

    # Access expects matrix indexed as origin_id/destination_id with durations in minutes.
    LOG.info("Computing access times for MN tracts ...")
    access_mn = compute_access_times(
        origin_df=tracts_mn,
        travel_matrix=matrix_mn,
        facilities=facilities_mn,
    )

    paths["tract_access"].parent.mkdir(parents=True, exist_ok=True)
    access_mn.to_parquet(paths["tract_access"], index=False)
    LOG.info("Profile %s tract access table written to %s", profile.profile_id, paths["tract_access"])

    # Minimal BEI: treat t_sys as the T component (longer time = worse).
    LOG.info("Computing MN BEI scores (MVP T-only, time-based) ...")
    if "t_sys" not in access_mn.columns:
        raise ValueError("Access table missing 't_sys'; cannot compute BEI.")
    bei_df = access_mn.copy()
    # Use robust_norm so higher t_sys -> higher t_score (worse access).
    bei_df["t_score"] = robust_norm(bei_df["t_sys"])
    # Stubs for other components so composite formula works.
    for col in ("s_score", "p_score", "c_score"):
        if col not in bei_df.columns:
            bei_df[col] = 0.0
    mn_bei = compute_composite_bei(bei_df)
    mn_bei.to_parquet(paths["tract_bei"], index=False)
    LOG.info("Profile %s tract BEI table written to %s", profile.profile_id, paths["tract_bei"])

    # Optional: write presentation manifest (profile-aware tables + GeoJSON).
    try:
        assets = get_profile_assets(profile)
        if not assets:
            assets = {
                "tract": {
                    "ground_only": {
                        "table": str(
                            paths["tract_bei"].resolve().relative_to(config.OUTPUT_DIR)
                        ),
                        "access_table": str(
                            paths["tract_access"].resolve().relative_to(config.OUTPUT_DIR)
                        ),
                    }
                }
            }
        methodology = {
            "data_sources": [
                "NIRD (hospital infrastructure)",
                "ACS 5-year 2022 (population, child population)",
                "TIGER/Line 2022 (tract geometry)",
                "RUCA (rurality classification)",
            ],
            "limitations": [
                "Minnesota-only tract origins; destinations limited to Minnesota plus nearby states.",
                "Ground-only travel scenario; air-access sensitivity is not included in this MVP manifest.",
            ],
            "scope_note": (
                "MN MVP presentation build scoped to Minnesota tracts with regional "
                "cross-border destinations; uses ground-only access and BEI outputs."
            ),
        }
        ui_defaults = {
            "geography_level": "tract",
            "metric": "bei",
            "map_center": list(profile.default_map_center),
            "map_zoom": profile.default_map_zoom,
            "narrative_order": [
                "burn_center_distribution",
                "rural_urban_travel_burden",
                "pediatric_access",
                "burn_bed_capacity",
            ],
        }
        manifest_path = write_presentation_manifest(
            profile=profile,
            assets=assets,
            methodology=methodology,
            ui_defaults=ui_defaults,
        )
        LOG.info("Profile %s manifest written to %s", profile.profile_id, manifest_path)
    except Exception:
        LOG.exception("Failed to write presentation manifest for profile %s", profile.profile_id)

    return access_mn, mn_bei


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    profile = get_profile()
    access_mn, mn_bei = run_mn_pipeline(profile.profile_id)
    print(f"MN high-detail pipeline complete. Tracts: {len(access_mn):,}, BEI rows: {len(mn_bei):,}")
    paths = _mn_paths(profile)
    print(f"  Access table: {paths['tract_access']}")
    print(f"  BEI table:    {paths['tract_bei']}")


if __name__ == "__main__":
    main()

