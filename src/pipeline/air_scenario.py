"""Air-access scenario: FAA data, ground-to-launch, air travel time, feasibility.

This module provides a minimal implementation that can be extended later without
breaking callers. It focuses on computing tract–facility air feasibility and an
aggregate air travel time consistent with the data-model spec.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from . import config

__all__ = [
    "AirLink",
    "load_faa_infrastructure",
    "compute_ground_to_launch",
    "compute_landing_to_facility",
    "compute_air_travel_times",
    "attach_ground_plus_air_access",
]


@dataclass
class AirLink:
    """Minimal representation of a feasible air link via launch/landing sites."""

    origin_id: str
    destination_id: str
    launch_airport_id: str
    landing_airport_id: str
    dispatch_min: float
    ground_to_launch_min: float
    flight_min: float
    landing_to_facility_min: float
    handoff_min: float

    @property
    def travel_time_min(self) -> float:
        return (
            self.dispatch_min
            + self.ground_to_launch_min
            + self.flight_min
            + self.landing_to_facility_min
            + self.handoff_min
        )


def load_faa_infrastructure(path: Path | None = None) -> pd.DataFrame:
    """Load FAA airport/heliport infrastructure and filter to operational records.

    Accepts either a pre-processed parquet with (location_id, facility_type, latitude,
    longitude, status) or the raw FAA APT_BASE.csv (mapped to that schema).
    """
    if path is None:
        parquet_path = config.FAA_DIR / "faa_airports_heliports.parquet"
        csv_path = config.FAA_DIR / "APT_BASE.csv"
        if parquet_path.exists():
            path = parquet_path
        elif csv_path.exists():
            path = csv_path
        else:
            raise FileNotFoundError(
                f"FAA infrastructure not found at {parquet_path} or {csv_path}. "
                "Place APT_BASE.csv in Data/external/faa/ or provide a pre-processed parquet."
            )

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"FAA infrastructure file not found at {path}.")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, low_memory=False).copy()
        # Map FAA APT_BASE columns to expected schema
        if "ARPT_ID" in df.columns and "location_id" not in df.columns:
            df["location_id"] = df["ARPT_ID"].astype(str).str.strip()
        if "LAT_DECIMAL" in df.columns and "latitude" not in df.columns:
            df["latitude"] = pd.to_numeric(df["LAT_DECIMAL"], errors="coerce")
        if "LONG_DECIMAL" in df.columns and "longitude" not in df.columns:
            df["longitude"] = pd.to_numeric(df["LONG_DECIMAL"], errors="coerce")
        if "ARPT_STATUS" in df.columns and "status" not in df.columns:
            df["status"] = df["ARPT_STATUS"].astype(str).str.strip().str.upper()
        if "SITE_TYPE_CODE" in df.columns and "facility_type" not in df.columns:
            _code = df["SITE_TYPE_CODE"].astype(str).str.strip().str.upper()
            df["facility_type"] = _code.map({"A": "AIRPORT", "H": "HELIPORT"}).fillna("AIRPORT")
        df = df.dropna(subset=["latitude", "longitude"])
    else:
        df = pd.read_parquet(path).copy()

    if "status" in df.columns:
        df = df[df["status"].astype(str).str.strip().str.upper() == "O"].copy()
    if "facility_type" in df.columns:
        df = df[df["facility_type"].astype(str).str.upper().isin(["HELIPORT", "AIRPORT"])].copy()
    if "location_id" not in df.columns:
        raise ValueError("FAA infrastructure must include a 'location_id' column (or ARPT_ID for CSV).")
    return df


def _haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Haversine distance between two point arrays in kilometers."""
    r = 6371.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return r * c


def _nearest_dest_haversine(
    origins: pd.DataFrame,
    origin_id_col: str,
    origin_lat: str,
    origin_lon: str,
    destinations: pd.DataFrame,
    dest_id_col: str,
    dest_lat: str,
    dest_lon: str,
    speed_kmh: float,
) -> pd.DataFrame:
    """For each origin, find nearest destination by straight-line distance; return duration_min from distance/speed."""
    o_id = origins[origin_id_col].astype(str)
    o_lat = origins[origin_lat].to_numpy(dtype=float)
    o_lon = origins[origin_lon].to_numpy(dtype=float)
    d_id = destinations[dest_id_col].astype(str).values
    d_lat = destinations[dest_lat].to_numpy(dtype=float)
    d_lon = destinations[dest_lon].to_numpy(dtype=float)
    # (N_origins, N_dests) distance matrix in km
    dist_km = _haversine_km(
        np.broadcast_to(o_lat[:, None], (len(o_lat), len(d_lat))),
        np.broadcast_to(o_lon[:, None], (len(o_lon), len(d_lon))),
        np.broadcast_to(d_lat[None, :], (len(o_lat), len(d_lat))),
        np.broadcast_to(d_lon[None, :], (len(o_lon), len(d_lon))),
    )
    idx_min = np.argmin(dist_km, axis=1)
    duration_min = (dist_km[np.arange(len(o_lat)), idx_min] / (speed_kmh / 60.0)).astype(float)
    return pd.DataFrame({
        origin_id_col: o_id.values,
        dest_id_col: d_id[idx_min],
        "distance_km": dist_km[np.arange(len(o_lat)), idx_min],
        "duration_min": duration_min,
    })


def compute_ground_to_launch(
    tracts: pd.DataFrame,
    faa_df: pd.DataFrame,
    out_path: Path | None = None,
    ground_speed_kmh: float | None = None,
) -> pd.DataFrame:
    """Compute ground-to-launch times from tracts to nearest airport (straight-line distance / speed). No Valhalla."""
    out = out_path or (config.TABLES_DIR / "air_ground_to_launch.parquet")
    speed = ground_speed_kmh or config.AIR_GROUND_SPEED_KMH
    airports = faa_df.rename(columns={"location_id": "airport_id", "latitude": "lat", "longitude": "lon"})
    df = _nearest_dest_haversine(
        origins=tracts,
        origin_id_col="GEOID",
        origin_lat="centroid_lat",
        origin_lon="centroid_lon",
        destinations=airports,
        dest_id_col="airport_id",
        dest_lat="lat",
        dest_lon="lon",
        speed_kmh=speed,
    )
    df = df.rename(columns={"GEOID": "tract_geoid", "airport_id": "launch_airport_id"})
    df = df[["tract_geoid", "launch_airport_id", "duration_min"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return df


def compute_landing_to_facility(
    facilities: pd.DataFrame,
    faa_df: pd.DataFrame,
    out_path: Path | None = None,
    ground_speed_kmh: float | None = None,
) -> pd.DataFrame:
    """Compute landing-to-facility times from nearest airport to each facility (straight-line / speed). No Valhalla."""
    out = out_path or (config.TABLES_DIR / "air_landing_to_facility.parquet")
    speed = ground_speed_kmh or config.AIR_GROUND_SPEED_KMH
    airports = faa_df.rename(columns={"location_id": "airport_id", "latitude": "lat", "longitude": "lon"})
    # Nearest airport to each facility: origins = facilities, destinations = airports
    df = _nearest_dest_haversine(
        origins=facilities,
        origin_id_col="AHA_ID",
        origin_lat="latitude",
        origin_lon="longitude",
        destinations=airports,
        dest_id_col="airport_id",
        dest_lat="lat",
        dest_lon="lon",
        speed_kmh=speed,
    )
    df = df.rename(columns={"AHA_ID": "facility_id", "airport_id": "landing_airport_id"})
    df = df[["facility_id", "landing_airport_id", "duration_min"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return df


def compute_air_travel_times(
    ground_to_launch: pd.DataFrame,
    landing_to_facility: pd.DataFrame,
    tracts: pd.DataFrame,
    facilities: pd.DataFrame,
    faa_df: pd.DataFrame,
    cruise_speed_mph: float | None = None,
) -> pd.DataFrame:
    """Compute end-to-end air travel times for feasible tract–facility pairs.

    Uses nearest launch airport per tract and nearest landing airport per facility,
    with flight time from launch to landing (straight-line / cruise speed).
    """
    cruise = cruise_speed_mph or config.AIR_CRUISE_SPEED_MPH
    # Nearest launch per tract
    gtl = (
        ground_to_launch.sort_values("duration_min")
        .groupby("tract_geoid", as_index=False)
        .first()
        .rename(columns={"duration_min": "duration_min_ground"})
    )
    # Nearest landing per facility
    ltf = (
        landing_to_facility.sort_values("duration_min")
        .groupby("facility_id", as_index=False)
        .first()
        .rename(columns={"duration_min": "duration_min_landing"})
    )

    # Cross join: each tract's best launch with each facility's best landing
    gtl["_key"] = 1
    ltf["_key"] = 1
    df = gtl.merge(ltf, on="_key").drop(columns=["_key"])
    gtl.drop(columns=["_key"], inplace=True)
    ltf.drop(columns=["_key"], inplace=True)

    # Launch and landing coords from FAA
    faa_coords = faa_df[["location_id", "latitude", "longitude"]].drop_duplicates("location_id")
    faa_coords["location_id"] = faa_coords["location_id"].astype(str)
    launch_coords = faa_coords.rename(
        columns={"location_id": "launch_airport_id", "latitude": "launch_lat", "longitude": "launch_lon"}
    )
    landing_coords = faa_coords.rename(
        columns={"location_id": "landing_airport_id", "latitude": "landing_lat", "longitude": "landing_lon"}
    )
    df["launch_airport_id"] = df["launch_airport_id"].astype(str)
    df["landing_airport_id"] = df["landing_airport_id"].astype(str)
    df = df.merge(launch_coords, on="launch_airport_id", how="left")
    df = df.merge(landing_coords, on="landing_airport_id", how="left")
    df["launch_lat"] = df["launch_lat"].fillna(0.0)
    df["launch_lon"] = df["launch_lon"].fillna(0.0)
    df["landing_lat"] = df["landing_lat"].fillna(0.0)
    df["landing_lon"] = df["landing_lon"].fillna(0.0)

    dist_km = _haversine_km(
        df["launch_lat"].to_numpy(dtype=float),
        df["launch_lon"].to_numpy(dtype=float),
        df["landing_lat"].to_numpy(dtype=float),
        df["landing_lon"].to_numpy(dtype=float),
    )
    cruise_km_per_min = cruise * 1.60934 / 60.0
    flight_min = dist_km / np.maximum(cruise_km_per_min, 1e-6)

    result = pd.DataFrame(
        {
            "origin_id": df["tract_geoid"].astype(str),
            "destination_id": df["facility_id"].astype(str),
            "mode": "air",
            "scenario": "ground_plus_air",
            "travel_time_min": (
                config.AIR_DISPATCH_MIN
                + df["duration_min_ground"].to_numpy(dtype=float)
                + flight_min
                + df["duration_min_landing"].to_numpy(dtype=float)
                + config.AIR_HANDOFF_MIN
            ),
            "dispatch_min": float(config.AIR_DISPATCH_MIN),
            "ground_to_launch_min": df["duration_min_ground"].to_numpy(dtype=float),
            "flight_min": flight_min,
            "landing_to_facility_min": df["duration_min_landing"].to_numpy(dtype=float),
            "handoff_min": float(config.AIR_HANDOFF_MIN),
            "launch_airport_id": df["launch_airport_id"],
            "landing_airport_id": df["landing_airport_id"],
            "is_feasible": True,
        }
    )
    return result


def attach_ground_plus_air_access(
    access_df: pd.DataFrame,
    air_matrix: pd.DataFrame,
    facilities: pd.DataFrame,
) -> pd.DataFrame:
    """Overlay a ground-plus-air scenario on top of ground-only access.

    Parameters
    ----------
    access_df:
        Ground-only access table with at least ``GEOID`` and ``t_sys``.
    air_matrix:
        Output from :func:`compute_air_travel_times`, containing
        ``origin_id``, ``destination_id``, and ``travel_time_min`` for
        feasible air paths.
    facilities:
        Facility table with ``AHA_ID`` and ``is_definitive`` flags so we
        can restrict air paths to definitive burn centers.

    Returns
    -------
    DataFrame
        Copy of ``access_df`` with two additional columns:

        - ``t_dir_air``: best air-only time to a definitive center
        - ``t_sys_air``: system time under the conditional
          ground-plus-air scenario, defined as
          ``min(t_sys_ground, t_dir_air)``.
    """
    if "GEOID" not in access_df.columns:
        raise ValueError("access_df must contain a 'GEOID' column.")
    if "t_sys" not in access_df.columns:
        raise ValueError("access_df must contain a 't_sys' column from ground-only access.")
    if "AHA_ID" not in facilities.columns:
        raise ValueError("facilities must contain column 'AHA_ID'.")
    if "is_definitive" not in facilities.columns:
        raise ValueError("facilities must contain boolean column 'is_definitive'.")

    definitive_ids = (
        facilities.loc[facilities["is_definitive"], "AHA_ID"]
        .astype(str)
        .unique()
    )
    air_def = air_matrix[air_matrix["destination_id"].isin(definitive_ids)].copy()
    if air_def.empty:
        out = access_df.copy()
        out["t_dir_air"] = np.inf
        out["t_sys_air"] = out["t_sys"]
        return out

    air_min = (
        air_def.groupby("origin_id", as_index=False)["travel_time_min"]
        .min()
        .rename(columns={"origin_id": "GEOID", "travel_time_min": "t_dir_air"})
    )

    out = access_df.copy()
    out["GEOID"] = out["GEOID"].astype(str)
    out = out.merge(air_min, on="GEOID", how="left")
    out["t_dir_air"] = out["t_dir_air"].fillna(np.inf)
    out["t_sys_air"] = np.minimum(
        out["t_sys"].to_numpy(dtype=float),
        out["t_dir_air"].to_numpy(dtype=float),
    )
    return out


def run_air_scenario(
    tracts: pd.DataFrame | None = None,
    facilities: pd.DataFrame | None = None,
    faa_path: Path | None = None,
    ground_to_launch_path: Path | None = None,
    landing_to_facility_path: Path | None = None,
    air_matrix_path: Path | None = None,
    skip_drive_matrices: bool = False,
) -> pd.DataFrame:
    """Run the air scenario: load or compute ground-to-launch and landing-to-facility,
    then compute air travel times. Returns the air matrix (tract x facility, air path).
    """
    from .routing_inputs import build_inputs

    if tracts is None or facilities is None:
        tracts, facilities = build_inputs()
    faa_df = load_faa_infrastructure(faa_path)

    gtl_path = ground_to_launch_path or (config.TABLES_DIR / "air_ground_to_launch.parquet")
    ltf_path = landing_to_facility_path or (config.TABLES_DIR / "air_landing_to_facility.parquet")
    air_path = air_matrix_path or (config.TABLES_DIR / "air_travel_times.parquet")

    if not skip_drive_matrices:
        if not gtl_path.exists():
            compute_ground_to_launch(tracts, faa_df, out_path=gtl_path)
        if not ltf_path.exists():
            compute_landing_to_facility(facilities, faa_df, out_path=ltf_path)

    gtl = pd.read_parquet(gtl_path)
    ltf = pd.read_parquet(ltf_path)
    air_df = compute_air_travel_times(
        gtl, ltf, tracts, facilities, faa_df=faa_df
    )
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    air_df.to_parquet(air_path, index=False)
    return air_df


def main() -> None:
    import argparse
    import logging

    from .routing_inputs import build_inputs

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Air-access scenario: tract–facility air travel times.")
    parser.add_argument(
        "--skip-drive",
        action="store_true",
        help="Skip recomputing ground-to-launch and landing-to-facility (use existing parquets).",
    )
    parser.add_argument(
        "--mn-only",
        action="store_true",
        help="Restrict to Minnesota tracts only (faster for testing).",
    )
    args = parser.parse_args()

    tracts, facilities = build_inputs()
    if args.mn_only:
        tracts = tracts[tracts["GEOID"].astype(str).str.startswith("27")].copy().reset_index(drop=True)

    run_air_scenario(tracts=tracts, facilities=facilities, skip_drive_matrices=args.skip_drive)
    print("Air scenario complete. air_travel_times.parquet written to Data/output/tables/.")


if __name__ == "__main__":
    main()

