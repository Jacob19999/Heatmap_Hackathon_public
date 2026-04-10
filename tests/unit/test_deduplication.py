from __future__ import annotations

import pandas as pd

from src.results_pipeline.stages.stage_00_data_audit import _deduplicate, _facility_class


def test_deduplicate_uses_aha_id() -> None:
    df = pd.DataFrame(
        {
            "AHA_ID": ["1", "1", "2"],
            "HOSPITAL_NAME": ["A", "A", "B"],
            "STATE": ["MN", "MN", "MN"],
        }
    )
    out = _deduplicate(df)
    assert len(out) == 2


def test_facility_class_derivation_basic_cases() -> None:
    df = pd.DataFrame(
        {
            "BURN_ADULT": [True, True, False, False, False],
            "BURN_PEDS": [False, True, False, False, True],
            "TRAUMA_ADULT": [False, False, True, False, False],
            "ADULT_TRAUMA_L1": [False, False, False, False, False],
            "ADULT_TRAUMA_L2": [False, False, False, False, False],
            "PEDS_TRAUMA_L1": [False, False, False, False, False],
            "PEDS_TRAUMA_L2": [False, False, False, False, False],
            "ABA_VERIFIED": [True, False, False, False, False],
        }
    )
    classes = _facility_class(df).tolist()
    assert "aba_verified_burn" in classes
    assert "trauma_only" in classes
    assert "pediatric_capable_burn" in classes
