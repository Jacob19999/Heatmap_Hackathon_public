from __future__ import annotations

import pandas as pd

from src.results_pipeline.utils.geography import derive_county_fips, derive_state_fips, derive_tract_geoid


def test_derive_state_fips_from_state_codes() -> None:
    s = pd.Series(["MN", "WI", "XX"])
    out = derive_state_fips(s)
    assert out.tolist() == ["27", "55", ""]


def test_derive_county_and_tract_from_existing_columns() -> None:
    df = pd.DataFrame({"TRACT_FIPS": ["27123000100", "55025000200"]})
    county = derive_county_fips(df)
    tract = derive_tract_geoid(df)
    assert county.tolist() == ["27123", "55025"]
    assert tract.tolist() == ["27123000100", "55025000200"]
