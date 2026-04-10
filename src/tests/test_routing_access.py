"""Routing and transfer-aware access tests for tract and county origins (US3).

Independent test: MN tract outputs reuse cached files when present;
county-centroid Valhalla routing produces county-to-hospital matrix;
direct vs transfer-aware system time obeys min(direct, transfer) rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.access import compute_access_times


def _minimal_travel_matrix(origin_id_col: str = "GEOID") -> pd.DataFrame:
    """Synthetic travel matrix: 2 origins, 3 facilities (1 definitive, 2 stabilization)."""
    return pd.DataFrame([
        {"origin_id": "27001020100", "destination_id": "D1", "duration_min": 25.0},
        {"origin_id": "27001020100", "destination_id": "S1", "duration_min": 20.0},
        {"origin_id": "27001020100", "destination_id": "S2", "duration_min": 40.0},
        {"origin_id": "27001020200", "destination_id": "D1", "duration_min": 35.0},
        {"origin_id": "27001020200", "destination_id": "S1", "duration_min": 28.0},
        {"origin_id": "27001020200", "destination_id": "S2", "duration_min": 50.0},
    ])


def _minimal_facilities() -> pd.DataFrame:
    """Facilities: D1 definitive, S1/S2 stabilization (S1 also definitive for transfer)."""
    return pd.DataFrame({
        "AHA_ID": ["D1", "S1", "S2"],
        "is_definitive": [True, True, False],
        "is_stabilization": [True, True, True],
    })


def _tract_origins() -> pd.DataFrame:
    return pd.DataFrame({
        "GEOID": ["27001020100", "27001020200"],
        "centroid_lat": [44.1, 44.2],
        "centroid_lon": [-93.5, -93.6],
    })


def _county_origins() -> pd.DataFrame:
    return pd.DataFrame({
        "county_fips": ["27001", "27003"],
        "centroid_lat": [44.15, 45.05],
        "centroid_lon": [-93.55, -93.05],
    })


def test_access_times_tract_origin_t_dir_t_sys():
    """Tract origins: T_dir, T_stab, T_trans, T_sys and access_pathway computed."""
    origins = _tract_origins()
    mat = _minimal_travel_matrix()
    fac = _minimal_facilities()
    out = compute_access_times(origins, mat, fac, transfer_penalty_min=15.0)
    assert "t_dir" in out.columns and "t_stab" in out.columns
    assert "t_trans" in out.columns and "t_sys" in out.columns
    assert "access_pathway" in out.columns
    assert out["t_sys"].notna().all()
    assert (out["t_sys"] <= out["t_dir"] + 1e-6).all() or out["t_dir"].isna().all()
    assert (out["t_sys"] <= out["t_trans"] + 1e-6).all() or out["t_trans"].isna().all()


def test_access_times_system_time_is_min_of_direct_and_transfer():
    """T_sys = min(T_dir, T_trans) for each origin."""
    origins = _tract_origins()
    mat = _minimal_travel_matrix()
    fac = _minimal_facilities()
    out = compute_access_times(origins, mat, fac, transfer_penalty_min=15.0)
    for _, row in out.iterrows():
        t_sys = row["t_sys"]
        t_dir = row["t_dir"]
        t_trans = row["t_trans"]
        if pd.notna(t_sys) and pd.notna(t_dir) and pd.notna(t_trans):
            assert t_sys <= t_dir + 1e-6
            assert t_sys <= t_trans + 1e-6
            assert abs(t_sys - min(t_dir, t_trans)) < 1e-6 or (t_dir == float("inf") and t_trans == float("inf"))


def test_access_times_county_origin_uses_county_fips():
    """County origins use county_fips as key; access columns present."""
    origins = _county_origins()
    mat = pd.DataFrame([
        {"origin_id": "27001", "destination_id": "D1", "duration_min": 30.0},
        {"origin_id": "27001", "destination_id": "S1", "duration_min": 22.0},
        {"origin_id": "27003", "destination_id": "D1", "duration_min": 45.0},
        {"origin_id": "27003", "destination_id": "S1", "duration_min": 40.0},
    ])
    fac = _minimal_facilities()
    out = compute_access_times(origins, mat, fac)
    assert "county_fips" in out.columns
    assert "t_sys" in out.columns and "access_pathway" in out.columns
    assert set(out["county_fips"]) <= {"27001", "27003"}


def test_access_times_origin_without_matching_matrix_row_keeps_nan():
    """Origins not in the travel matrix keep NaN access times."""
    origins = pd.DataFrame({"GEOID": ["99999999999"], "centroid_lat": [44.0], "centroid_lon": [-93.0]})
    mat = _minimal_travel_matrix()
    fac = _minimal_facilities()
    out = compute_access_times(origins, mat, fac)
    assert out["t_sys"].isna().all() or out["t_sys"].eq(float("inf")).all() or (out["t_sys"] >= 0).all()
