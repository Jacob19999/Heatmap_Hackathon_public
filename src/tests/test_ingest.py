"""Facility classification tests: supply_weight and peds_weight mapping per plan.md."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.ingest import compute_classification
from pipeline import config
import pandas as pd


@pytest.fixture
def sample_facilities():
    """Minimal rows covering plan.md classification cases."""
    return pd.DataFrame({
        "AHA_ID": ["1", "2", "3", "4", "5"],
        "BURN_ADULT": [1, 1, 0, 0, 1],
        "BURN_PEDS": [0, 1, 0, 0, 1],
        "ABA_VERIFIED": ["Yes", "Yes", "No", "No", "No"],
        "BC_STATE_DESIGNATED": ["No", "No", "No", "No", "Yes"],
        "TRAUMA_ADULT": [0, 0, 1, 1, 0],
        "ADULT_TRAUMA_L1": [0, 0, 1, 0, 0],
        "ADULT_TRAUMA_L2": [0, 0, 0, 1, 0],
        "PEDS_TRAUMA_L1": [0, 0, 0, 0, 0],
        "PEDS_TRAUMA_L2": [0, 0, 0, 0, 0],
    })


def test_supply_weight_aba_verified(sample_facilities):
    """ABA_VERIFIED=Yes -> supply_weight 1.0."""
    df = compute_classification(sample_facilities)
    assert df.loc[df["AHA_ID"] == "1", "supply_weight"].iloc[0] == 1.0
    assert df.loc[df["AHA_ID"] == "2", "supply_weight"].iloc[0] == 1.0


def test_supply_weight_bc_state_only(sample_facilities):
    """BC_STATE_DESIGNATED=Yes, not ABA -> 0.85."""
    df = compute_classification(sample_facilities)
    row = df[df["AHA_ID"] == "5"].iloc[0]
    assert row["supply_weight"] == 0.85


def test_is_definitive_mutually_exclusive(sample_facilities):
    """is_definitive and is_stabilization are mutually exclusive."""
    df = compute_classification(sample_facilities)
    assert (~(df["is_definitive"] & df["is_stabilization"])).all()
