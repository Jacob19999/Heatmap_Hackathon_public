from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


def cache_key(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()  # noqa: S324 - deterministic cache key only


def _series_fingerprint(series: pd.Series) -> str:
    normalized = pd.Series(series).reset_index(drop=True)
    hashed = pd.util.hash_pandas_object(normalized, index=False)
    return hashlib.sha1(hashed.values.tobytes()).hexdigest()  # noqa: S324 - deterministic cache key only


def cache_path(cache_dir: Path, key: str, ext: str = "parquet") -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.{ext}"


def read_cached_frame(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    return None


def write_cached_frame(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Unsupported cache extension: {path.suffix}")
    return path


def get_or_compute_nearest_travel(
    origins_lat: pd.Series,
    origins_lon: pd.Series,
    origin_ids: pd.Series,
    facilities_lat: pd.Series,
    facilities_lon: pd.Series,
    cache_dir: Path,
    scenario_id: str = "ground_only",
    km_per_minute: float = 0.8,
) -> pd.DataFrame:
    """Return a DataFrame with origin_id and travel_minutes (nearest facility). Use cache when present."""
    from ..utils.routing import nearest_facility_travel_minutes

    key = cache_key(
        "stage03_nearest",
        scenario_id,
        str(len(origins_lat)),
        str(len(facilities_lat)),
        str(km_per_minute),
        _series_fingerprint(pd.to_numeric(origins_lat, errors="coerce").round(6)),
        _series_fingerprint(pd.to_numeric(origins_lon, errors="coerce").round(6)),
        _series_fingerprint(origin_ids.astype(str)),
        _series_fingerprint(pd.to_numeric(facilities_lat, errors="coerce").round(6)),
        _series_fingerprint(pd.to_numeric(facilities_lon, errors="coerce").round(6)),
    )
    path = cache_path(cache_dir, key, "parquet")
    cached = read_cached_frame(path)
    if cached is not None and "origin_id" in cached.columns and "travel_minutes" in cached.columns:
        return cached
    minutes = nearest_facility_travel_minutes(
        origins_lat, origins_lon, facilities_lat, facilities_lon, km_per_minute=km_per_minute
    )
    out = pd.DataFrame({"origin_id": origin_ids.values, "travel_minutes": minutes.values})
    write_cached_frame(out, path)
    return out
