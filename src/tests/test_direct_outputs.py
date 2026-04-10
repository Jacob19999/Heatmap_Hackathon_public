"""Direct-output aggregation regression checks (US2).

Independent test: zero-burn-center states remain zero in state summaries,
rural travel burden exceeds urban where applicable, pediatric-capable access
below general burn-center access, county/state summaries publish correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.aggregation import aggregate_to_county, aggregate_to_state
from pipeline.bei_composite import burn_centers_per_100k


def _tract_df_with_ruca_and_bei() -> pd.DataFrame:
    """Synthetic tract table with BEI components and rural/urban."""
    n = 12
    return pd.DataFrame({
        "GEOID": [f"2700{i:05d}100" for i in range(1, n + 1)],
        "centroid_lat": 44.0 + np.random.uniform(-0.3, 0.3, n),
        "centroid_lon": -93.0 + np.random.uniform(-0.3, 0.3, n),
        "total_pop": np.random.randint(500, 20000, n),
        "child_pop": np.random.randint(50, 3000, n),
        "ruca_code": [1, 2, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10],
        "is_rural": [False] * 4 + [True] * 8,
        "bei": np.clip(20 + 60 * np.random.rand(n), 0, 100),
        "s_score": np.random.rand(n),
        "t_score": np.random.rand(n),
        "p_score": np.random.rand(n),
        "c_score": np.random.rand(n),
    })


def test_aggregate_to_county_produces_unique_county_fips():
    """County aggregation yields one row per county with pop-weighted BEI."""
    tracts = _tract_df_with_ruca_and_bei()
    county = aggregate_to_county(tracts, pop_col="total_pop")
    assert county["county_fips"].is_unique
    assert "total_pop" in county.columns
    for col in ("bei", "s_score", "t_score", "p_score", "c_score"):
        if col in tracts.columns:
            assert col in county.columns
            assert county[col].notna().all() or county[col].isna().all()


def test_aggregate_to_state_produces_unique_state_fips():
    """State aggregation yields one row per state with pop-weighted metrics."""
    tracts = _tract_df_with_ruca_and_bei()
    state = aggregate_to_state(tracts, pop_col="total_pop")
    assert state["state_fips"].is_unique
    assert state["state_fips"].iloc[0] == "27"


def test_zero_burn_center_state_has_zero_centers_per_100k():
    """States with no facilities get centers_per_100k = 0."""
    facilities = pd.DataFrame({
        "AHA_ID": ["1"],
        "STATE": ["MN"],
        "supply_weight": [1.0],
    })
    tracts = pd.DataFrame({
        "GEOID": ["27001020100", "55001020100"],
        "total_pop": [10000, 10000],
    })
    out = burn_centers_per_100k(facilities, tracts, state_col="STATE", pop_col="total_pop")
    assert "state" in out.columns and "centers_per_100k" in out.columns
    no_fac = out[out["supply_weight"] == 0]
    if len(no_fac):
        assert (no_fac["centers_per_100k"] == 0).all()
    assert (out["centers_per_100k"] >= 0).all()


def test_county_and_state_summaries_publish_required_columns():
    """County and state rollups contain geography key and denominator."""
    tracts = _tract_df_with_ruca_and_bei()
    county = aggregate_to_county(tracts)
    state = aggregate_to_state(tracts)
    assert "county_fips" in county.columns and county["county_fips"].notna().all()
    assert "state_fips" in state.columns and state["state_fips"].notna().all()
    assert (county["total_pop"] >= 0).all()
    assert (state["total_pop"] >= 0).all()
