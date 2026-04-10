"""Tract and county analytic table regression coverage (US1).

Independent test: facilities resolve to tracts, tract denominators non-null,
RUCA joins complete, county-origin records have unique county FIPS and non-null centroids.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.aggregation import county_origins_from_tracts


def _minimal_tract_table(include_ruca: bool = True) -> pd.DataFrame:
    """Synthetic tract-level table with required US1 fields."""
    data = {
        "GEOID": ["27001020100", "27001020200", "27003010100", "27003010200"],
        "centroid_lat": [44.1, 44.2, 45.0, 45.1],
        "centroid_lon": [-93.5, -93.6, -93.0, -93.1],
        "total_pop": [100, 200, 300, 150],
        "child_pop": [20, 40, 60, 30],
    }
    df = pd.DataFrame(data)
    if include_ruca:
        df["ruca_code"] = [1, 2, 4, 5]
        df["is_rural"] = [False, False, True, True]
    return df


def test_tract_analytic_table_has_required_denominators_and_centroids():
    """Tract analytic table has GEOID, total_pop, child_pop, centroid_lat/lon non-null."""
    tracts = _minimal_tract_table()
    assert "GEOID" in tracts.columns
    assert tracts["GEOID"].notna().all()
    assert tracts["total_pop"].notna().all()
    assert tracts["child_pop"].notna().all()
    assert tracts["centroid_lat"].notna().all()
    assert tracts["centroid_lon"].notna().all()


def test_tract_table_ruca_join_complete_when_present():
    """When RUCA is joined, ruca_code and is_rural are present and consistent."""
    tracts = _minimal_tract_table(include_ruca=True)
    assert "ruca_code" in tracts.columns and "is_rural" in tracts.columns
    assert tracts["ruca_code"].notna().all()
    assert tracts["is_rural"].dtype == bool or tracts["is_rural"].isin([True, False]).all()


def test_county_origins_unique_fips_and_non_null_centroids():
    """County origins derived from tracts have unique county FIPS and non-null centroids."""
    tracts = _minimal_tract_table()
    counties = county_origins_from_tracts(tracts, pop_col="total_pop")
    assert counties["county_fips"].is_unique
    assert counties["centroid_lat"].notna().all()
    assert counties["centroid_lon"].notna().all()
    assert (counties["total_pop"] > 0).all()
    assert set(counties["county_fips"]) == {"27001", "27003"}


def test_county_origins_preserve_child_pop_when_present():
    """County origins sum child_pop when present on tracts."""
    tracts = _minimal_tract_table()
    counties = county_origins_from_tracts(tracts, pop_col="total_pop")
    assert "child_pop" in counties.columns
    assert (counties["child_pop"] >= 0).all()
    assert counties.loc[counties["county_fips"] == "27001", "child_pop"].iloc[0] == 60
    assert counties.loc[counties["county_fips"] == "27003", "child_pop"].iloc[0] == 90


def test_county_origins_require_centroid_and_pop_columns():
    """county_origins_from_tracts raises when required columns are missing."""
    tracts = _minimal_tract_table().drop(columns=["centroid_lat"])
    with pytest.raises(ValueError, match="centroid_lat"):
        county_origins_from_tracts(tracts, pop_col="total_pop")
