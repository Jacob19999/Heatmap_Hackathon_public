from __future__ import annotations

import logging

import pandas as pd

from . import config
from .aggregation import county_origins_from_tracts
from .augment import build_analytic_table
from .geocode import assign_tract_from_tiger, load_batch_results_and_merge
from .ingest import ingest_nird

LOG = logging.getLogger(__name__)

GEOCODE_RESULTS_PATH = config.TABLES_DIR / "GeocodeResults.csv"


def _geocode_facilities(facilities: pd.DataFrame) -> pd.DataFrame:
    """Geocode facilities from pre-existing GeocodeResults.csv only (no geocoding API calls)."""
    results_csv = GEOCODE_RESULTS_PATH
    if not results_csv.exists():
        raise FileNotFoundError(
            f"Geocode results file not found at {results_csv}. "
            "Place your pre-geocoded Census batch results there (GeocodeResults.csv). "
            "The pipeline does not call the geocoding API; use the file that is already geocoded."
        )
    LOG.info("Loading pre-geocoded coordinates from %s (no API calls).", results_csv)
    facilities_geo = load_batch_results_and_merge(facilities, results_path=results_csv)
    with_coords = (facilities_geo["latitude"].notna() & facilities_geo["longitude"].notna()).sum()
    with_tract = (facilities_geo["tract_geoid"].notna() & (facilities_geo["tract_geoid"] != "")).sum()
    LOG.info(
        "After CSV merge: %d/%d facilities have coords, %d have tract.",
        int(with_coords),
        len(facilities_geo),
        int(with_tract),
    )

    # Fill any remaining tracts via TIGER point-in-polygon (local only, no API)
    missing_tract = (
        (facilities_geo["tract_geoid"].isna() | (facilities_geo["tract_geoid"] == "")) &
        facilities_geo["latitude"].notna()
    )
    if missing_tract.any():
        LOG.info(
            "Running TIGER point-in-polygon for %d facilities missing tract_geoid.",
            int(missing_tract.sum()),
        )
        facilities_geo = assign_tract_from_tiger(facilities_geo)

    return facilities_geo


def build_facilities() -> pd.DataFrame:
    """Build geocoded facility destinations for routing without tract augmentation."""
    LOG.info("Loading and classifying NIRD facilities ...")
    facilities, report = ingest_nird()
    LOG.info("Facilities loaded: %s", report)

    LOG.info("Geocoding facilities ...")
    facilities_geo = _geocode_facilities(facilities)

    missing_coords = facilities_geo["latitude"].isna() | facilities_geo["longitude"].isna()
    if missing_coords.any():
        LOG.warning(
            "%d facilities without coordinates will be excluded from routing.",
            int(missing_coords.sum()),
        )
        facilities_geo = facilities_geo[~missing_coords].copy()

    if "AHA_ID" not in facilities_geo.columns:
        raise ValueError("Expected column 'AHA_ID' in facilities after ingest; cannot build destinations.")

    return facilities_geo


def build_tract_origins() -> pd.DataFrame:
    """Build tract-level analytic table for use as routing origins (MN high-detail path).

    Returns tract DataFrame with GEOID, centroid_lat, centroid_lon, total_pop,
    child_pop, and optional RUCA fields. Use this when only origins are needed;
    use build_inputs() when both tract origins and facility destinations are needed.
    """
    facilities_geo = build_facilities()
    LOG.info("Building tract analytic table (TIGER + ACS + RUCA) ...")
    tracts = build_analytic_table(facilities_geo)
    if "GEOID" not in tracts.columns:
        raise ValueError("Tract analytic table missing 'GEOID' column.")
    if "centroid_lat" not in tracts.columns or "centroid_lon" not in tracts.columns:
        raise ValueError("Tract analytic table missing centroid_lat/centroid_lon.")
    LOG.info("Tract origins: %d", len(tracts))
    return tracts


def build_county_origins(pop_col: str = "total_pop") -> pd.DataFrame:
    """Build county-level routing origins from tract analytic table (USA low-detail path).

    Returns county DataFrame with county_fips, centroid_lat, centroid_lon, total_pop,
    child_pop. For caching or persistence, callers (e.g. usa_low_detail_county_valhalla)
    may write/read parquet; this function does not perform I/O.
    """
    tracts = build_tract_origins()
    LOG.info("Deriving county origins from %d tracts ...", len(tracts))
    return county_origins_from_tracts(tracts, pop_col=pop_col)


def build_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build origins (tracts) and destinations (facilities) for routing."""
    facilities_geo = build_facilities()
    tracts = build_tract_origins()
    LOG.info(
        "Origins (tracts): %d  |  Destinations (facilities): %d",
        len(tracts),
        len(facilities_geo),
    )
    return tracts, facilities_geo

