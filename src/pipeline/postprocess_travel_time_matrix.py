"""
Postprocess a saved travel-time matrix by filling remaining infinite durations.

Fallback hierarchy:
1. Keep the original routed duration when finite.
2. For remaining infinities, impute from nearby tracts that have a finite travel
   time to the same destination.
3. If no suitable neighbors exist, use a conservative straight-line estimate.

The raw duration column is preserved, and the filled values are written to a
separate parquet so downstream consumers can choose which column to use.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from . import config
from .aggregation import county_origins_from_tracts
from .routing_inputs import build_facilities, build_tract_origins

LOG = logging.getLogger(__name__)


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: np.ndarray,
    lon2: np.ndarray,
) -> np.ndarray:
    """Return Haversine distance in kilometers from one point to many points."""
    r = 6_371.0
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    return r * 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_filled{input_path.suffix}")


def _load_reference_data(origin_ids: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build origin and facility reference tables used for fallback calculations."""
    facilities = build_facilities()
    tracts = build_tract_origins()
    tract_origin_ref = (
        tracts.rename(columns={"GEOID": "origin_id"})[["origin_id", "centroid_lat", "centroid_lon"]]
        .drop_duplicates("origin_id")
        .copy()
    )
    county_origins = county_origins_from_tracts(tracts)
    county_origin_ref = (
        county_origins.rename(columns={"county_fips": "origin_id"})[["origin_id", "centroid_lat", "centroid_lon"]]
        .drop_duplicates("origin_id")
        .copy()
    )
    destination_ref = (
        facilities.rename(columns={"AHA_ID": "destination_id"})[["destination_id", "latitude", "longitude"]]
        .drop_duplicates("destination_id")
        .copy()
    )
    destination_ref["destination_id"] = destination_ref["destination_id"].astype(str)
    tract_origin_ref["origin_id"] = tract_origin_ref["origin_id"].astype(str)
    county_origin_ref["origin_id"] = county_origin_ref["origin_id"].astype(str)

    matrix_origin_ids = set(origin_ids.astype(str).unique())
    tract_matches = int(tract_origin_ref["origin_id"].isin(matrix_origin_ids).sum())
    county_matches = int(county_origin_ref["origin_id"].isin(matrix_origin_ids).sum())
    if county_matches > tract_matches:
        origin_ref = county_origin_ref
        LOG.info("Using county origin reference table (%d id matches).", county_matches)
    else:
        origin_ref = tract_origin_ref
        LOG.info("Using tract origin reference table (%d id matches).", tract_matches)
    return origin_ref, destination_ref


def _build_neighbor_cache(
    origin_ref: pd.DataFrame,
    inf_origin_ids: pd.Series,
    search_k: int,
) -> dict[str, list[str]]:
    """Return nearest tract ids for each origin that needs filling."""
    lat_all = origin_ref["centroid_lat"].to_numpy(dtype=float)
    lon_all = origin_ref["centroid_lon"].to_numpy(dtype=float)
    ids_all = origin_ref["origin_id"].to_numpy(dtype=str)
    pos_lookup = {origin_id: i for i, origin_id in enumerate(ids_all)}

    neighbor_cache: dict[str, list[str]] = {}
    for origin_id in tqdm(inf_origin_ids.astype(str).unique(), desc="Neighbor lookup", unit="origin", leave=True):
        pos = pos_lookup.get(origin_id)
        if pos is None:
            neighbor_cache[origin_id] = []
            continue

        distances = _haversine_km(lat_all[pos], lon_all[pos], lat_all, lon_all)
        order = np.argsort(distances)
        neighbors: list[str] = []
        for idx in order:
            if idx == pos:
                continue
            neighbors.append(ids_all[idx])
            if len(neighbors) >= search_k:
                break
        neighbor_cache[origin_id] = neighbors
    return neighbor_cache


def fill_travel_time_matrix(
    input_path: Path,
    output_path: Path | None = None,
    neighbor_search_k: int = 25,
    neighbor_use_k: int = 5,
    neighbor_min_valid: int = 3,
    detour_factor: float = 1.4,
    speed_kmh: float = 65.0,
) -> pd.DataFrame:
    """Fill infinite durations in a saved matrix and write a new parquet file."""
    if neighbor_search_k < neighbor_use_k:
        raise ValueError("neighbor_search_k must be >= neighbor_use_k")
    if neighbor_min_valid < 1 or neighbor_min_valid > neighbor_use_k:
        raise ValueError("neighbor_min_valid must be between 1 and neighbor_use_k")
    if detour_factor <= 0 or speed_kmh <= 0:
        raise ValueError("detour_factor and speed_kmh must be positive")

    if not input_path.exists():
        raise FileNotFoundError(f"Travel-time matrix not found: {input_path}")

    df = pd.read_parquet(input_path).copy()
    required = {"origin_id", "destination_id", "duration_min"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Matrix is missing required columns: {sorted(missing)}")

    df["origin_id"] = df["origin_id"].astype(str)
    df["destination_id"] = df["destination_id"].astype(str)
    df["duration_min_raw"] = df["duration_min"]
    df["duration_min_filled"] = df["duration_min"]
    df["duration_fill_method"] = np.where(np.isfinite(df["duration_min"]), "raw", "unfilled_inf")
    df["duration_fill_neighbor_count"] = 0
    df["fallback_haversine_km"] = np.nan
    df["fallback_estimated_road_km"] = np.nan

    inf_mask = ~np.isfinite(df["duration_min"])
    inf_count = int(inf_mask.sum())
    LOG.info("Loaded %d matrix rows from %s (%d inf rows).", len(df), input_path, inf_count)

    if inf_count == 0:
        save_path = output_path or _default_output_path(input_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(save_path, index=False)
        LOG.info("No inf rows found. Wrote unchanged filled matrix to %s", save_path)
        return df

    origin_ref, destination_ref = _load_reference_data(df["origin_id"])
    origin_lookup = origin_ref.set_index("origin_id")
    destination_lookup = destination_ref.set_index("destination_id")

    finite_lookup = df.loc[np.isfinite(df["duration_min"]), ["destination_id", "origin_id", "duration_min"]]
    finite_lookup = finite_lookup.drop_duplicates(["destination_id", "origin_id"])
    finite_series = finite_lookup.set_index(["destination_id", "origin_id"])["duration_min"]

    inf_origin_ids = df.loc[inf_mask, "origin_id"]
    neighbor_cache = _build_neighbor_cache(origin_ref, inf_origin_ids, search_k=neighbor_search_k)

    neighbor_fills = 0
    straight_line_fills = 0
    still_unfilled = 0

    inf_indices = df.index[inf_mask]
    for idx in tqdm(inf_indices, desc="Fill inf rows", unit="row", leave=True):
        origin_id = df.at[idx, "origin_id"]
        destination_id = df.at[idx, "destination_id"]

        neighbor_values: list[float] = []
        for neighbor_origin_id in neighbor_cache.get(origin_id, []):
            value = finite_series.get((destination_id, neighbor_origin_id))
            if value is None or not np.isfinite(value):
                continue
            neighbor_values.append(float(value))
            if len(neighbor_values) >= neighbor_use_k:
                break

        if len(neighbor_values) >= neighbor_min_valid:
            df.at[idx, "duration_min_filled"] = float(np.median(neighbor_values))
            df.at[idx, "duration_fill_method"] = "neighbor_same_destination"
            df.at[idx, "duration_fill_neighbor_count"] = len(neighbor_values)
            neighbor_fills += 1
            continue

        if origin_id not in origin_lookup.index or destination_id not in destination_lookup.index:
            still_unfilled += 1
            continue

        origin = origin_lookup.loc[origin_id]
        destination = destination_lookup.loc[destination_id]
        haversine_km = float(
            _haversine_km(
                float(origin["centroid_lat"]),
                float(origin["centroid_lon"]),
                np.array([float(destination["latitude"])]),
                np.array([float(destination["longitude"])]),
            )[0]
        )
        estimated_road_km = haversine_km * detour_factor
        estimated_minutes = estimated_road_km / speed_kmh * 60.0

        df.at[idx, "duration_min_filled"] = estimated_minutes
        df.at[idx, "duration_fill_method"] = "straight_line"
        df.at[idx, "fallback_haversine_km"] = haversine_km
        df.at[idx, "fallback_estimated_road_km"] = estimated_road_km
        straight_line_fills += 1

    save_path = output_path or _default_output_path(input_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(save_path, index=False)

    LOG.info(
        "Filled matrix written to %s (neighbor=%d, straight_line=%d, unfilled=%d).",
        save_path,
        neighbor_fills,
        straight_line_fills,
        still_unfilled,
    )
    return df


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill remaining inf durations in a saved travel-time matrix.")
    parser.add_argument(
        "--input",
        type=Path,
        default=config.TRAVEL_TIME_MATRIX_PATH,
        help="Path to the raw matrix parquet.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path for the filled output parquet. Defaults to '<input>_filled.parquet'.",
    )
    parser.add_argument("--neighbor-search-k", type=int, default=25, help="Nearby tracts to scan per inf row.")
    parser.add_argument("--neighbor-use-k", type=int, default=5, help="Maximum valid neighbors to use.")
    parser.add_argument(
        "--neighbor-min-valid",
        type=int,
        default=3,
        help="Minimum same-destination neighbors required before using neighbor fill.",
    )
    parser.add_argument(
        "--detour-factor",
        type=float,
        default=1.4,
        help="Multiplier applied to Haversine distance for straight-line fallback.",
    )
    parser.add_argument(
        "--speed-kmh",
        type=float,
        default=65.0,
        help="Average speed used to convert fallback road kilometers to minutes.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO)
    filled = fill_travel_time_matrix(
        input_path=args.input,
        output_path=args.output,
        neighbor_search_k=args.neighbor_search_k,
        neighbor_use_k=args.neighbor_use_k,
        neighbor_min_valid=args.neighbor_min_valid,
        detour_factor=args.detour_factor,
        speed_kmh=args.speed_kmh,
    )

    method_counts = filled["duration_fill_method"].value_counts(dropna=False).to_dict()
    print(f"Rows: {len(filled):,}")
    print(f"Fill methods: {method_counts}")
    print(
        "Remaining inf in raw / filled: "
        f"{int((~np.isfinite(filled['duration_min_raw'])).sum()):,} / "
        f"{int((~np.isfinite(filled['duration_min_filled'])).sum()):,}"
    )


if __name__ == "__main__":
    main()
