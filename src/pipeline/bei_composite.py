"""
Composite BEI and companion metrics; Challenge Area 3 outputs: burn centers per 100k,
rural vs urban travel burden, pediatric access, burn-bed capacity.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

LOG = logging.getLogger(__name__)

# Census state FIPS (2-digit). NIRD uses 2-letter abbreviations; tracts use FIPS.
STATE_ABBR_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09",
    "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17",
    "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31",
    "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
    "WI": "55", "WY": "56",
}
FIPS_TO_ABBR = {v: k for k, v in STATE_ABBR_TO_FIPS.items()}


def state_fips_to_abbr(df: pd.DataFrame, state_col: str = "state") -> pd.DataFrame:
    """Return a copy of df with state column as 2-letter abbreviation (for display)."""
    out = df.copy()
    if state_col in out.columns:
        out[state_col] = out[state_col].astype(str).str.zfill(2).map(FIPS_TO_ABBR).fillna(out[state_col])
    return out


def _facility_state_to_fips(series: pd.Series) -> pd.Series:
    """Convert facility state column (abbreviation or FIPS) to 2-digit FIPS for joining with tracts."""
    s = series.astype(str).str.strip().str.upper()
    out = s.replace(STATE_ABBR_TO_FIPS)
    # Zero-pad numeric state codes (e.g. 6 -> 06) to match tract GEOID
    def pad(v: str) -> str:
        try:
            n = int(float(v))
            if 1 <= n <= 56:
                return f"{n:02d}"
        except (ValueError, TypeError):
            pass
        return v
    return out.apply(pad)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in km (Haversine)."""
    R = 6371
    a = np.radians(lat2 - lat1)
    b = np.radians(lon2 - lon1)
    x = np.sin(a / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(b / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(x))


def burn_centers_per_100k(
    facilities: pd.DataFrame,
    tracts: pd.DataFrame,
    state_col: str = "STATE",
    pop_col: str = "total_pop",
) -> pd.DataFrame:
    """Aggregate by state: sum(supply_weight) per state, sum(pop); centers per 100k = (supply_weight_sum / pop_sum) * 1e5."""
    fac = facilities[facilities["supply_weight"] > 0].copy()
    fac["state"] = _facility_state_to_fips(fac[state_col])
    tract_state = tracts.copy()
    if "state_fips" in tract_state.columns:
        tract_state["state"] = tract_state["state_fips"]
    elif "GEOID" in tract_state.columns:
        tract_state["state"] = tract_state["GEOID"].astype(str).str[:2]
    else:
        tract_state["state"] = ""
    pop_by_state = tract_state.groupby("state")[pop_col].sum()
    weight_by_state = fac.groupby("state")["supply_weight"].sum()
    combined = pd.DataFrame({"pop": pop_by_state, "supply_weight": weight_by_state}).fillna(0)
    combined["centers_per_100k"] = np.where(combined["pop"] > 0, (combined["supply_weight"] / combined["pop"]) * 1e5, 0)
    return combined.reset_index()


def _facility_lat_lon_columns(facilities: pd.DataFrame) -> tuple[str | None, str | None]:
    """Return (lat_col, lon_col) for facilities; accept latitude/longitude or Lat/Long (Census)."""
    for lat, lon in [("latitude", "longitude"), ("Lat", "Long")]:
        if lat in facilities.columns and lon in facilities.columns:
            return lat, lon
    return None, None


def _travel_burden_from_state_centroids(
    tracts: pd.DataFrame,
    facilities: pd.DataFrame,
    state_col: str = "STATE",
) -> pd.Series:
    """When facility coords are missing: use tract state centroid as proxy burn-center location.
    Returns series of nearest_burn_time_min (minutes) indexed like tracts."""
    if "centroid_lat" not in tracts.columns or "centroid_lon" not in tracts.columns:
        return pd.Series(np.nan, index=tracts.index)
    tract_state = tracts["GEOID"].astype(str).str[:2] if "GEOID" in tracts.columns else pd.Series("", index=tracts.index)
    def_fac = facilities[facilities["is_definitive"]].copy()
    if len(def_fac) == 0:
        return pd.Series(np.nan, index=tracts.index)
    def_fac["state_fips"] = _facility_state_to_fips(def_fac[state_col])
    states_with_center = set(def_fac["state_fips"].dropna().unique())
    tr = tracts.copy()
    tr["_state"] = tract_state
    # State centroid = pop-weighted or plain mean of tract centroids per state
    if "total_pop" in tr.columns and (tr["total_pop"] > 0).any():
        pop = tr["total_pop"].clip(lower=1)
        state_lat = tr.groupby("_state").apply(
            lambda g: (g["centroid_lat"] * g["total_pop"]).sum() / g["total_pop"].sum()
        )
        state_lon = tr.groupby("_state").apply(
            lambda g: (g["centroid_lon"] * g["total_pop"]).sum() / g["total_pop"].sum()
        )
    else:
        state_lat = tr.groupby("_state")["centroid_lat"].mean()
        state_lon = tr.groupby("_state")["centroid_lon"].mean()
    times = []
    n_tracts = len(tr)
    print(
        f"[rural_urban_travel_burden] Estimating state-centroid travel times for "
        f"{n_tracts:,} tracts (no facility coordinates available)..."
    )
    for i, (_, row) in enumerate(tr.iterrows(), start=1):
        st = row["_state"]
        if st not in states_with_center:
            times.append(np.nan)
            continue
        lat, lon = state_lat.get(st, np.nan), state_lon.get(st, np.nan)
        if pd.isna(lat) or pd.isna(lon):
            times.append(np.nan)
            continue
        km = haversine_km(row["centroid_lat"], row["centroid_lon"], lat, lon)
        times.append(km / 0.6)
        if i % 5000 == 0 or i == n_tracts:
            pct = 100.0 * i / n_tracts
            print(
                f"[rural_urban_travel_burden]   state-centroid rows processed: "
                f"{i:,} / {n_tracts:,} ({pct:4.1f}%)"
            )
    return pd.Series(times, index=tracts.index)


def rural_urban_travel_burden(
    tracts: pd.DataFrame,
    facilities: pd.DataFrame,
    time_col: str = "nearest_burn_time_min",
    rural_col: str = "is_rural",
    state_col: str = "STATE",
) -> pd.DataFrame:
    """Stratify tracts by is_rural; compare median (and distribution) of travel time to nearest burn center."""
    lat_col, lon_col = _facility_lat_lon_columns(facilities)
    if time_col not in tracts.columns:
        has_centroids = "centroid_lat" in tracts.columns and "centroid_lon" in tracts.columns
        if has_centroids and lat_col and lon_col:
            def_min = facilities[facilities["is_definitive"]].copy()
            def_min = def_min[def_min[lat_col].notna() & def_min[lon_col].notna()]
            if len(def_min) > 0:
                times = []
                n_tracts = len(tracts)
                n_facilities = len(def_min)
                print(
                    f"[rural_urban_travel_burden] Computing nearest burn times via Haversine for "
                    f"{n_tracts:,} tracts × {n_facilities:,} facilities..."
                )
                for i, (_, t) in enumerate(tracts.iterrows(), start=1):
                    dmin = min(
                        haversine_km(t["centroid_lat"], t["centroid_lon"], f[lat_col], f[lon_col])
                        for _, f in def_min.iterrows()
                    )
                    times.append(dmin / 0.6)
                    if i % 5000 == 0 or i == n_tracts:
                        pct = 100.0 * i / n_tracts
                        print(
                            f"[rural_urban_travel_burden]   tract rows processed: "
                            f"{i:,} / {n_tracts:,} ({pct:4.1f}%)"
                        )
                tracts = tracts.copy()
                tracts["nearest_burn_time_min"] = times
                time_col = "nearest_burn_time_min"
            elif has_centroids:
                # No facility coords: use state-centroid proxy so we still return a summary
                tracts = tracts.copy()
                print(
                    "[rural_urban_travel_burden] No facility coordinates with is_definitive; "
                    "falling back to state-centroid travel times."
                )
                tracts["nearest_burn_time_min"] = _travel_burden_from_state_centroids(tracts, facilities, state_col)
                time_col = "nearest_burn_time_min"
            else:
                return pd.DataFrame()
        elif has_centroids:
            # No facility coords: state-centroid fallback
            tracts = tracts.copy()
            tracts["nearest_burn_time_min"] = _travel_burden_from_state_centroids(tracts, facilities, state_col)
            time_col = "nearest_burn_time_min"
        else:
            return pd.DataFrame()
    if rural_col not in tracts.columns:
        tracts = tracts.copy()
        tracts[rural_col] = False
    # Drop NaN times for summary so median/mean are meaningful
    with_time = tracts[tracts[time_col].notna()] if time_col in tracts.columns else tracts
    if len(with_time) == 0:
        return pd.DataFrame({rural_col: [], "median": [], "mean": [], "count": []})
    summary = with_time.groupby(rural_col)[time_col].agg(["median", "mean", "count"]).reset_index()
    return summary


def pediatric_access_per_capita(
    facilities: pd.DataFrame,
    tracts: pd.DataFrame,
    state_col: str = "STATE",
    child_pop_col: str = "child_pop",
) -> pd.DataFrame:
    """Count pediatric-capable facilities (peds_weight > 0) per state; peds per child_pop (per 100k)."""
    fac = facilities[facilities["peds_weight"] > 0].copy()
    fac["state"] = _facility_state_to_fips(fac[state_col])
    tract_state = tracts.copy()
    if "state_fips" in tract_state.columns:
        tract_state["state"] = tract_state["state_fips"]
    elif "GEOID" in tract_state.columns:
        tract_state["state"] = tract_state["GEOID"].astype(str).str[:2]
    else:
        tract_state["state"] = ""
    child_by_state = tract_state.groupby("state")[child_pop_col].sum()
    peds_count = fac.groupby("state").size()
    combined = pd.DataFrame({"child_pop": child_by_state, "peds_facilities": peds_count}).fillna(0)
    combined["peds_per_100k_children"] = np.where(combined["child_pop"] > 0, (combined["peds_facilities"] / combined["child_pop"]) * 1e5, 0)
    return combined.reset_index()


def burn_beds_per_100k(
    facilities: pd.DataFrame,
    tracts: pd.DataFrame,
    state_col: str = "STATE",
    pop_col: str = "total_pop",
) -> pd.DataFrame:
    """Aggregate BURN_BEDS by state; beds per 100k = (beds_sum / pop_sum) * 1e5."""
    bed_col = "burn_beds" if "burn_beds" in facilities.columns else "BURN_BEDS"
    fac = facilities.copy()
    fac["state"] = _facility_state_to_fips(fac[state_col])
    beds_by_state = fac.groupby("state")[bed_col].sum()
    tract_state = tracts.copy()
    if "GEOID" in tract_state.columns:
        tract_state["state"] = tract_state["GEOID"].astype(str).str[:2]
    else:
        tract_state["state"] = ""
    pop_by_state = tract_state.groupby("state")[pop_col].sum()
    combined = pd.DataFrame({"pop": pop_by_state, "beds": beds_by_state}).fillna(0)
    combined["beds_per_100k"] = np.where(combined["pop"] > 0, (combined["beds"] / combined["pop"]) * 1e5, 0)
    return combined.reset_index()


def compute_composite_bei(
    tract_df: pd.DataFrame,
    weights: tuple[float, float, float, float] | None = None,
) -> pd.DataFrame:
    """BEI = 100 * (wS*S + wT*T + wP*P + wC*C). Expects s_score, t_score, p_score, c_score in tract_df."""
    w = weights or config.BEI_WEIGHTS
    out = tract_df.copy()
    for col in ("s_score", "t_score", "p_score", "c_score"):
        if col not in out.columns:
            out[col] = 0.0
    out["bei"] = 100.0 * (w[0] * out["s_score"] + w[1] * out["t_score"] + w[2] * out["p_score"] + w[3] * out["c_score"])
    out["bei_percentile"] = out["bei"].rank(pct=True) * 100
    return out


def compute_scenario_delta(
    ground_df: pd.DataFrame,
    air_df: pd.DataFrame,
    id_col: str = "tract_geoid",
) -> pd.DataFrame:
    """Compute scenario deltas between ground-only and ground-plus-air BEI.

    Parameters
    ----------
    ground_df:
        Tract-level BEI records for the ground-only scenario. Must include
        the identifier column, ``bei``, and ``t_sys``.
    air_df:
        Tract-level BEI records for the ground-plus-air scenario with the
        same identifier column, ``bei``, and ``t_sys`` (typically
        ``t_sys_air``).
    id_col:
        Column name used to join ground and air records. Defaults to the
        data-model key ``tract_geoid``; callers can pass ``\"GEOID\"`` if
        working directly with tract tables.

    Returns
    -------
    DataFrame
        Scenario delta table matching the spec, with:

        - ``tract_geoid``
        - ``bei_ground``, ``bei_air``, ``bei_delta``
        - ``t_sys_ground``, ``t_sys_air``, ``t_delta``
        - ``air_feasible`` (bool)
        - ``air_materially_helps`` (bool; configurable threshold via BEI delta)
    """
    g = ground_df.rename(
        columns={
            id_col: "tract_geoid",
            "bei": "bei_ground",
            "t_sys": "t_sys_ground",
        }
    )
    a = air_df.rename(
        columns={
            id_col: "tract_geoid",
            "bei": "bei_air",
            "t_sys": "t_sys_air",
        }
    )
    merged = g.merge(a[["tract_geoid", "bei_air", "t_sys_air"]], on="tract_geoid", how="left")
    merged["bei_air"] = merged["bei_air"].fillna(merged["bei_ground"])
    merged["t_sys_air"] = merged["t_sys_air"].fillna(merged["t_sys_ground"])

    merged["bei_delta"] = merged["bei_ground"] - merged["bei_air"]
    merged["t_delta"] = merged["t_sys_ground"] - merged["t_sys_air"]

    merged["air_feasible"] = merged["t_sys_air"] < merged["t_sys_ground"]
    merged["air_materially_helps"] = merged["bei_delta"] > 2.0

    cols = [
        "tract_geoid",
        "bei_ground",
        "bei_air",
        "bei_delta",
        "t_sys_ground",
        "t_sys_air",
        "t_delta",
        "air_feasible",
        "air_materially_helps",
    ]
    return merged[cols]
