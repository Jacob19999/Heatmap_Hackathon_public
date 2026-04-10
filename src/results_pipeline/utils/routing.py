from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def nearest_facility_travel_minutes(
    origins_lat: "pd.Series",
    origins_lon: "pd.Series",
    facilities_lat: "pd.Series",
    facilities_lon: "pd.Series",
    km_per_minute: float = 0.8,
) -> "pd.Series":
    """For each origin, compute straight-line distance to nearest facility and convert to minutes.
    km_per_minute approximates ground speed (e.g. 0.8 ≈ 48 km/h)."""
    import numpy as np
    import pandas as pd

    olat = np.radians(origins_lat.values.astype(float).reshape(-1, 1))
    olon = np.radians(origins_lon.values.astype(float).reshape(-1, 1))
    flat = np.radians(facilities_lat.values.astype(float).reshape(1, -1))
    flon = np.radians(facilities_lon.values.astype(float).reshape(1, -1))
    r = 6371.0
    dlat = flat - olat
    dlon = flon - olon
    a = np.sin(dlat / 2) ** 2 + np.cos(olat) * np.cos(flat) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(np.clip(a, 0, 1)), np.sqrt(np.clip(1 - a, 0, 1)))
    dist_km = r * c
    min_km = np.nanmin(dist_km, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        minutes = np.where(min_km >= 0, min_km / km_per_minute, np.nan)
    return pd.Series(minutes, index=origins_lat.index)
