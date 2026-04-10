"""Foundational tests for the USA low-detail county routing path."""
from pathlib import Path

import pandas as pd

from pipeline import config
from pipeline.aggregation import county_origins_from_tracts


def test_county_origins_have_unique_fips_and_centroids():
    """County origins derived from tracts have unique FIPS and non-null centroids."""
    # Minimal synthetic tract table with two counties, multiple tracts each.
    data = {
        "GEOID": ["01001020100", "01001020200", "01003010100"],
        "centroid_lat": [32.1, 32.2, 33.0],
        "centroid_lon": [-86.5, -86.6, -86.0],
        "total_pop": [100, 200, 300],
        "child_pop": [30, 40, 50],
    }
    tracts = pd.DataFrame(data)
    counties = county_origins_from_tracts(tracts, pop_col="total_pop")

    # Expect two counties (01001, 01003).
    assert set(counties["county_fips"]) == {"01001", "01003"}
    # Centroids and populations should be non-null.
    assert counties["centroid_lat"].notna().all()
    assert counties["centroid_lon"].notna().all()
    assert (counties["total_pop"] > 0).all()

