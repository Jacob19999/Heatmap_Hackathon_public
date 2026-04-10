from __future__ import annotations

import pandas as pd


TRUE_VALUES = {"1", "y", "yes", "true", "t"}
FALSE_VALUES = {"0", "n", "no", "false", "f", ""}


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_boolean(value: object) -> bool | None:
    text = normalize_text(value).lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return None


def coerce_bool_series(series: pd.Series) -> pd.Series:
    mapped = series.map(normalize_boolean)
    mapped = mapped.where(mapped.notna(), False)
    return mapped.astype(bool)


def coerce_int_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def normalize_yes_no_like_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = coerce_bool_series(out[col])
    return out
