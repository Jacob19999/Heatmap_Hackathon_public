"""USA low-detail (county-level) aggregation for driving-distance BEI.

This script takes a national tract-level BEI/access table and rolls it up to
county-level metrics suitable for the `usa_low_detail_county_tab` dashboard
view. It uses population-weighted aggregation as specified in the BEI spec.

Alternatively, run_usa_county_pipeline_from_matrix() computes county-level
access and BEI directly from the county–hospital travel time matrix (no tract
aggregation).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import config
from .access import compute_access_times
from .aggregation import aggregate_to_county, county_aggregation_paths, validate_county_only_profile
from .bei_components import robust_norm
from .bei_composite import compute_composite_bei
from .presentation_scope import get_profile
from .export import write_presentation_manifest, get_profile_assets
from .routing_inputs import build_facilities

LOG = logging.getLogger(__name__)

COUNTY_ORIGINS_CACHE_PATH = config.TABLES_DIR / "usa_low_detail_county_county_origins.parquet"


def run_usa_county_pipeline_from_matrix() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run USA low-detail county pipeline from the county travel time matrix.

    Loads county origins, the county–hospital matrix (from profile path),
    computes access times and BEI, writes county_access and county_bei tables
    and the presentation manifest. Returns (county_access, county_bei).
    """
    profile = get_profile("usa_low_detail_county")
    validate_county_only_profile(profile)

    if not COUNTY_ORIGINS_CACHE_PATH.exists():
        raise FileNotFoundError(
            f"County origins not found at {COUNTY_ORIGINS_CACHE_PATH}. "
            "Run usa_low_detail_county_valhalla (or at least build county origins) first."
        )
    matrix_path = Path(profile.matrix_raw_path)
    if not matrix_path.exists():
        raise FileNotFoundError(
            f"County travel time matrix not found at {matrix_path}. "
            "Run usa_low_detail_county_valhalla to build it."
        )

    LOG.info("Loading county origins from %s", COUNTY_ORIGINS_CACHE_PATH)
    county_origins = pd.read_parquet(COUNTY_ORIGINS_CACHE_PATH)
    LOG.info("Loading county travel time matrix from %s", matrix_path)
    matrix = pd.read_parquet(matrix_path)
    if not {"origin_id", "destination_id", "duration_min"}.issubset(matrix.columns):
        raise ValueError("Matrix must have columns origin_id, destination_id, duration_min.")
    matrix["origin_id"] = matrix["origin_id"].astype(str)

    facilities = build_facilities()
    LOG.info("Computing county-level access times …")
    county_access = compute_access_times(
        origin_df=county_origins,
        travel_matrix=matrix,
        facilities=facilities,
    )

    paths = county_aggregation_paths(profile)
    paths["county_access_table"].parent.mkdir(parents=True, exist_ok=True)
    county_access.to_parquet(paths["county_access_table"], index=False)
    LOG.info("County access table written to %s", paths["county_access_table"])

    if "t_sys" not in county_access.columns:
        raise ValueError("Access table missing 't_sys'; cannot compute BEI.")
    bei_df = county_access.copy()
    bei_df["t_score"] = robust_norm(bei_df["t_sys"])
    for col in ("s_score", "p_score", "c_score"):
        if col not in bei_df.columns:
            bei_df[col] = 0.0
    county_bei = compute_composite_bei(bei_df)
    county_bei.to_parquet(paths["county_bei_table"], index=False)
    LOG.info("County BEI table written to %s", paths["county_bei_table"])

    try:
        assets = get_profile_assets(profile)
        if not assets:
            assets = {
                "county": {
                    "ground_only": {
                        "table": str(paths["county_bei_table"].resolve().relative_to(config.OUTPUT_DIR)),
                        "access_table": str(paths["county_access_table"].resolve().relative_to(config.OUTPUT_DIR)),
                    }
                }
            }
        methodology = {
            "data_sources": [
                "NIRD (hospital infrastructure)",
                "ACS 5-year 2022 (population)",
                "TIGER/Line 2022 (county centroids)",
                "Valhalla (county centroid → hospital travel times)",
            ],
            "limitations": [
                "County-level origins (population-weighted centroids); national destinations.",
                "Ground-only travel scenario.",
            ],
            "scope_note": "USA low-detail county presentation from county–hospital matrix.",
        }
        ui_defaults = {
            "geography_level": "county",
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

    return county_access, county_bei


def build_usa_low_detail_county(
    tract_bei_path: Path | None = None,
    pop_col: str = "total_pop",
) -> pd.DataFrame:
    """Aggregate national tract-level BEI to county level for low-detail tab.

    Parameters
    ----------
    tract_bei_path:
        Path to the national tract-level BEI/access table containing at least:
        - `GEOID` (11-digit tract FIPS)
        - `bei` (composite BEI)
        - `t_sys` (system travel time in minutes) or equivalent access field
        - `total_pop` (population denominator for weighting)
        If None, defaults to `Data/output/tables/national_tract_bei.parquet`.
    pop_col:
        Name of the population column used for weighting.
    """
    profile = get_profile("usa_low_detail_county")
    validate_county_only_profile(profile)

    if tract_bei_path is None:
        # Preferred national tract-level BEI output.
        tract_bei_path = config.TABLES_DIR / "national_tract_bei.parquet"

    tract_bei_path = Path(tract_bei_path)
    if not tract_bei_path.exists():
        # For hackathon MVP, gracefully fall back to existing MN tract BEI so the
        # county-level aggregation path and frontend wiring can be exercised even
        # before the full national run is complete.
        mn_candidates = [
            config.TABLES_DIR / "mn_high_detail_tract_bei.parquet",
            config.TABLES_DIR / "mn_mvp_tract_bei.parquet",
        ]
        for candidate in mn_candidates:
            if candidate.exists():
                LOG.warning(
                    "National tract-level BEI table not found at %s; "
                    "falling back to MN-only tract BEI at %s for county "
                    "aggregation (MVP/testing only).",
                    tract_bei_path,
                    candidate,
                )
                tract_bei_path = candidate
                break
        else:
            raise FileNotFoundError(
                f"National tract-level BEI table not found at {tract_bei_path} "
                "and no MN-level fallback (mn_high_detail_tract_bei.parquet or "
                "mn_mvp_tract_bei.parquet) present in Data/output/tables. "
                "Run the BEI pipeline first or point this function at the "
                "correct tract-level output path."
            )

    LOG.info("Loading national tract-level BEI table from %s", tract_bei_path)
    tract_df = pd.read_parquet(tract_bei_path)

    if "GEOID" not in tract_df.columns:
        raise ValueError("Expected `GEOID` column with tract FIPS in tract-level BEI table.")
    if pop_col not in tract_df.columns:
        raise ValueError(f"Expected population column {pop_col!r} in tract-level BEI table.")

    LOG.info("Aggregating BEI and components to county level using %s as weights ...", pop_col)
    county_df = aggregate_to_county(tract_df, pop_col=pop_col)

    paths = county_aggregation_paths(profile)
    out_path = paths["county_bei_table"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    county_df.to_parquet(out_path, index=False)
    LOG.info(
        "USA low-detail county BEI table written to %s (%d counties).",
        out_path,
        len(county_df),
    )

    return county_df


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    df = build_usa_low_detail_county()
    print(f"USA low-detail county aggregation complete. Counties: {len(df):,}")


if __name__ == "__main__":
    main()

