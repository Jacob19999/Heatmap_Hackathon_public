from __future__ import annotations

import pandas as pd


STATE_TO_FIPS = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "DC": "11",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
}


def normalize_fips(value: str | int | None, width: int) -> str:
    if value is None:
        return ""
    return str(value).strip().zfill(width)


def derive_state_fips(state_series: pd.Series) -> pd.Series:
    return state_series.astype(str).str.strip().str.upper().map(STATE_TO_FIPS).fillna("")


def derive_county_fips(df: pd.DataFrame) -> pd.Series:
    if "COUNTY_FIPS" in df.columns:
        return df["COUNTY_FIPS"].map(lambda v: normalize_fips(v, 5))
    if "county_fips" in df.columns:
        return df["county_fips"].map(lambda v: normalize_fips(v, 5))
    if "TRACT_FIPS" in df.columns:
        return df["TRACT_FIPS"].astype(str).str[:5].map(lambda v: normalize_fips(v, 5))
    if "tract_fips" in df.columns:
        return df["tract_fips"].astype(str).str[:5].map(lambda v: normalize_fips(v, 5))
    return pd.Series([""] * len(df), index=df.index)


def derive_tract_geoid(df: pd.DataFrame) -> pd.Series:
    if "TRACT_FIPS" in df.columns:
        return df["TRACT_FIPS"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    if "tract_fips" in df.columns:
        return df["tract_fips"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    county = derive_county_fips(df)
    return county + "000000"
