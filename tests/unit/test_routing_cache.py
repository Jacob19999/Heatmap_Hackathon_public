from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.results_pipeline.io.cache import cache_key, cache_path, get_or_compute_nearest_travel, read_cached_frame, write_cached_frame
from src.results_pipeline.utils.routing import haversine_km, nearest_facility_travel_minutes


def test_haversine_km() -> None:
    d = haversine_km(44.0, -93.0, 45.0, -93.0)
    assert d > 100
    assert d < 120


def test_nearest_facility_travel_minutes() -> None:
    origins_lat = pd.Series([44.0, 45.0])
    origins_lon = pd.Series([-93.0, -94.0])
    fac_lat = pd.Series([44.5, 44.1])
    fac_lon = pd.Series([-93.5, -93.1])
    out = nearest_facility_travel_minutes(origins_lat, origins_lon, fac_lat, fac_lon, km_per_minute=1.0)
    assert len(out) == 2
    assert out.min() >= 0


def test_cache_key() -> None:
    k = cache_key("stage03", "ground_only", "100")
    assert len(k) == 40
    assert cache_key("a", "b") != cache_key("a", "c")


def test_cache_path(tmp_path: Path) -> None:
    p = cache_path(tmp_path, "abc123", "parquet")
    assert p.name == "abc123.parquet"
    assert p.parent == tmp_path


def test_write_read_cached_frame(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    p = tmp_path / "x.parquet"
    write_cached_frame(df, p)
    assert p.exists()
    out = read_cached_frame(p)
    assert out is not None
    assert out.shape == (2, 2)


def test_get_or_compute_nearest_travel(tmp_path: Path) -> None:
    lat = pd.Series([44.0])
    lon = pd.Series([-93.0])
    ids = pd.Series(["27123000100"])
    flat = pd.Series([44.5])
    flon = pd.Series([-93.5])
    df = get_or_compute_nearest_travel(lat, lon, ids, flat, flon, tmp_path, "ground_only", 0.8)
    assert "origin_id" in df.columns
    assert "travel_minutes" in df.columns
    assert len(df) == 1
    df2 = get_or_compute_nearest_travel(lat, lon, ids, flat, flon, tmp_path, "ground_only", 0.8)
    assert df2["travel_minutes"].iloc[0] == df["travel_minutes"].iloc[0]
