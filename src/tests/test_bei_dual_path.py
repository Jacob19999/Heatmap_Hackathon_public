"""BEI component and composite regression tests for county low-detail outputs (US4).

Independent test: component bounds, composite decomposability, intuitive ordering
for known good/bad geographies, consistent county/state rankings from county-level outputs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config
from pipeline.aggregation import aggregate_to_county, aggregate_to_state
from pipeline.bei_composite import compute_composite_bei


def _county_bei_df() -> pd.DataFrame:
    """Synthetic county-level table with BEI components (low-detail path)."""
    return pd.DataFrame({
        "county_fips": ["27001", "27003", "27005"],
        "s_score": [0.8, 0.3, 0.2],
        "t_score": [0.7, 0.4, 0.3],
        "p_score": [0.6, 0.5, 0.4],
        "c_score": [0.9, 0.2, 0.1],
        "total_pop": [100000, 50000, 20000],
    })


def test_composite_bei_bounds_zero_to_100():
    """Composite BEI is in [0, 100] for any component scores in [0, 1]."""
    df = _county_bei_df()
    out = compute_composite_bei(df)
    assert "bei" in out.columns
    assert (out["bei"] >= 0).all() and (out["bei"] <= 100).all()


def test_composite_bei_decomposable_weights():
    """BEI = 100 * (wS*S + wT*T + wP*P + wC*C) with config weights."""
    w = config.BEI_WEIGHTS
    row = {"s_score": 0.25, "t_score": 0.25, "p_score": 0.25, "c_score": 0.25}
    df = pd.DataFrame([row])
    out = compute_composite_bei(df, weights=w)
    expected = 100.0 * (w[0] + w[1] + w[2] + w[3]) * 0.25
    assert abs(out["bei"].iloc[0] - expected) < 1e-6


def test_composite_bei_higher_scores_higher_bei():
    """County with higher component scores has higher BEI (better access)."""
    df = _county_bei_df()
    out = compute_composite_bei(df)
    # 27001 has highest components -> highest BEI
    bei_27001 = out.loc[out["county_fips"] == "27001", "bei"].iloc[0]
    bei_27005 = out.loc[out["county_fips"] == "27005", "bei"].iloc[0]
    assert bei_27001 > bei_27005


def test_aggregate_to_county_preserves_ranking_consistency():
    """County rollup from tract BEI preserves relative ordering (pop-weighted)."""
    tracts = pd.DataFrame({
        "GEOID": ["27001020100", "27001020200", "27003010100"],
        "county_fips": ["27001", "27001", "27003"],
        "total_pop": [10000, 10000, 20000],
        "bei": [80.0, 70.0, 30.0],
        "s_score": [0.8, 0.7, 0.3],
        "t_score": [0.8, 0.7, 0.3],
        "p_score": [0.8, 0.7, 0.3],
        "c_score": [0.8, 0.7, 0.3],
    })
    county = aggregate_to_county(tracts)
    assert county["county_fips"].is_unique
    # 27001 should have higher BEI than 27003 (better access)
    bei_01 = county.loc[county["county_fips"] == "27001", "bei"].iloc[0]
    bei_03 = county.loc[county["county_fips"] == "27003", "bei"].iloc[0]
    assert bei_01 > bei_03


def test_county_and_state_rollups_have_geography_keys():
    """County and state BEI rollups contain geography key and metrics."""
    tracts = pd.DataFrame({
        "GEOID": ["27001020100", "27001020200", "27003010100"],
        "total_pop": [10000, 10000, 20000],
        "bei": [80.0, 70.0, 30.0],
        "s_score": [0.8, 0.7, 0.3],
        "t_score": [0.8, 0.7, 0.3],
        "p_score": [0.8, 0.7, 0.3],
        "c_score": [0.8, 0.7, 0.3],
    })
    county = aggregate_to_county(tracts)
    state = aggregate_to_state(tracts)
    assert "county_fips" in county.columns and "state_fips" in state.columns
    assert "bei" in county.columns and "total_pop" in county.columns
    assert "bei" in state.columns or "total_pop" in state.columns
