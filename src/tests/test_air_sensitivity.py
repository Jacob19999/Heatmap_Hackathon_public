"""Ground-vs-air delta regression tests (US5).

Independent test: air paths improve access only where feasible;
deltas are non-negative (better access = lower t_sys, higher BEI);
county/state summaries identify regions with meaningful air sensitivity.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.aggregation import aggregate_air_delta_to_county
from pipeline.bei_composite import compute_scenario_delta
from pipeline.air_scenario import attach_ground_plus_air_access


def _ground_access_df() -> pd.DataFrame:
    return pd.DataFrame({
        "GEOID": ["27001020100", "27001020200", "27003010100"],
        "t_sys": [75.0, 60.0, 90.0],
        "t_dir": [80.0, 65.0, 95.0],
        "t_stab": [50.0, 45.0, 70.0],
    })


def test_scenario_delta_bei_delta_and_t_delta_signs():
    """When air improves access: bei_air > bei_ground so bei_delta <= 0; t_sys_air < t_sys_ground so t_delta >= 0."""
    ground = pd.DataFrame({
        "GEOID": ["27001020100", "27001020200"],
        "bei": [40.0, 50.0],
        "t_sys": [75.0, 60.0],
    })
    air = pd.DataFrame({
        "GEOID": ["27001020100", "27001020200"],
        "bei": [55.0, 52.0],
        "t_sys": [45.0, 55.0],
    })
    delta = compute_scenario_delta(ground, air, id_col="GEOID")
    assert "bei_delta" in delta.columns and "t_delta" in delta.columns
    # bei_delta = bei_ground - bei_air; when air helps (higher BEI), bei_delta <= 0
    assert (delta["bei_delta"] <= 0 + 1e-6).all()
    # t_delta = t_sys_ground - t_sys_air; when air helps (lower time), t_delta >= 0
    assert (delta["t_delta"] >= -1e-6).all()


def test_scenario_delta_air_feasible_when_t_sys_air_less_than_ground():
    """air_feasible is True when t_sys_air < t_sys_ground."""
    ground = pd.DataFrame({
        "GEOID": ["A", "B"],
        "bei": [50.0, 50.0],
        "t_sys": [80.0, 40.0],
    })
    air = pd.DataFrame({
        "GEOID": ["A", "B"],
        "bei": [60.0, 50.0],
        "t_sys": [50.0, 40.0],
    })
    delta = compute_scenario_delta(ground, air, id_col="GEOID")
    assert "air_feasible" in delta.columns
    a = delta[delta["tract_geoid"] == "A"].iloc[0]
    b = delta[delta["tract_geoid"] == "B"].iloc[0]
    assert a["air_feasible"] == True
    assert b["air_feasible"] == False


def test_attach_ground_plus_air_access_t_sys_air_min_of_ground_and_air():
    """t_sys_air = min(t_sys_ground, t_dir_air) so air never worsens system time."""
    access = _ground_access_df()
    air_matrix = pd.DataFrame({
        "origin_id": ["27001020100", "27001020200"],
        "destination_id": ["D1", "D1"],
        "travel_time_min": [40.0, 70.0],
    })
    facilities = pd.DataFrame({
        "AHA_ID": ["D1"],
        "is_definitive": [True],
    })
    out = attach_ground_plus_air_access(access, air_matrix, facilities)
    assert "t_sys_air" in out.columns and "t_dir_air" in out.columns
    assert (out["t_sys_air"] <= out["t_sys"] + 1e-6).all()


def test_scenario_delta_air_materially_helps_threshold():
    """air_materially_helps is True when bei_delta > 2.0 (implementation: ground - air > 2)."""
    ground = pd.DataFrame({
        "GEOID": ["A", "B"],
        "bei": [50.0, 50.0],
        "t_sys": [80.0, 70.0],
    })
    air = pd.DataFrame({
        "GEOID": ["A", "B"],
        "bei": [45.0, 51.0],
        "t_sys": [40.0, 65.0],
    })
    delta = compute_scenario_delta(ground, air, id_col="GEOID")
    assert "air_materially_helps" in delta.columns
    a = delta[delta["tract_geoid"] == "A"].iloc[0]
    assert a["bei_delta"] > 2.0
    assert a["air_materially_helps"] == True


def test_aggregate_air_delta_to_county():
    """County-level aggregation of air-scenario deltas yields one row per county with pop-weighted means when tract_df given."""
    delta_df = pd.DataFrame({
        "tract_geoid": ["27001020100", "27001020200", "27003010100"],
        "bei_ground": [40.0, 50.0, 45.0],
        "bei_air": [55.0, 52.0, 48.0],
        "bei_delta": [-15.0, -2.0, -3.0],
        "t_sys_ground": [75.0, 60.0, 90.0],
        "t_sys_air": [45.0, 55.0, 70.0],
        "t_delta": [30.0, 5.0, 20.0],
        "air_feasible": [True, True, True],
        "air_materially_helps": [True, False, True],
    })
    tract_df = pd.DataFrame({
        "GEOID": ["27001020100", "27001020200", "27003010100"],
        "total_pop": [1000, 500, 800],
    })
    county = aggregate_air_delta_to_county(delta_df, tract_df=tract_df, pop_col="total_pop")
    assert "county_fips" in county.columns
    assert county.shape[0] == 2
    # 27001: two tracts; 27003: one tract
    c27001 = county[county["county_fips"] == "27001"].iloc[0]
    assert c27001["total_pop"] == 1500
    # pop-weighted bei_ground: (40*1000 + 50*500)/1500 = 43.33...
    assert 43.0 <= c27001["bei_ground"] <= 44.0
    assert "bei_delta" in county.columns and "air_feasible" in county.columns
