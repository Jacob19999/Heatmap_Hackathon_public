from __future__ import annotations

import pandas as pd

from src.results_pipeline.utils.normalization import coerce_bool_series, coerce_int_series


def test_coerce_bool_series_handles_yes_no_and_numeric() -> None:
    s = pd.Series(["Yes", "no", 1, 0, "", None])
    out = coerce_bool_series(s)
    assert out.tolist() == [True, False, True, False, False, False]


def test_coerce_int_series_handles_blank_and_text() -> None:
    s = pd.Series(["10", "2", "", None, "bad"])
    out = coerce_int_series(s)
    assert out.tolist() == [10, 2, 0, 0, 0]
