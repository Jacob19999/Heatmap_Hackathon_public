"""
Access pathway: T_dir (direct to nearest definitive), T_stab (nearest stabilization),
T_trans (stabilize + transfer penalty + transfer to definitive), T_sys = min(T_dir, T_trans).
"""
from __future__ import annotations

import logging

import pandas as pd

from . import config

LOG = logging.getLogger(__name__)


def compute_access_times(
    origin_df: pd.DataFrame,
    travel_matrix: pd.DataFrame,
    facilities: pd.DataFrame,
    transfer_penalty_min: float | None = None,
    stabilization_threshold_min: float | None = None,
) -> pd.DataFrame:
    """Compute T_dir, T_stab, T_trans, T_sys, tier penalty Δ, access_pathway per origin (ground_only).

    `origin_df` may be a tract-level or county-level table; it must contain a
    column that matches the `origin_id` values in `travel_matrix`. By default
    this function will look for a `GEOID` column (tracts) and fall back to
    `county_fips` when present (counties).
    """
    tau = transfer_penalty_min or config.TRANSFER_PENALTY_MIN
    stab_thresh = stabilization_threshold_min or config.STABILIZATION_THRESHOLD_MIN
    definitive = facilities[facilities["is_definitive"]].copy()
    stabilization = facilities[facilities["is_stabilization"] | facilities["is_definitive"]].copy()
    # Pivot matrix: rows = tract_geoid, cols = facility id, value = duration_min
    mat = travel_matrix.pivot(index="origin_id", columns="destination_id", values="duration_min")
    out = origin_df.copy()
    out["t_dir"] = float("nan")
    out["t_stab"] = float("nan")
    out["t_trans"] = float("nan")
    out["t_sys"] = float("nan")
    out["t_delta"] = float("nan")
    out["access_pathway"] = ""
    # Determine which column in origin_df is the routing key.
    if "GEOID" in out.columns:
        key_col = "GEOID"
    elif "county_fips" in out.columns:
        key_col = "county_fips"
    else:
        raise ValueError("origin_df must contain either 'GEOID' or 'county_fips' to match origin_id.")

    ids = [g for g in mat.index if g in out[key_col].astype(str).values]
    from tqdm.auto import tqdm
    it = tqdm(ids, desc="Access times", unit="origin", leave=True)
    for oid in it:
        it.set_postfix_str(f"origin {oid}")
        row = mat.loc[oid]
        def_durs = row[row.index.isin(definitive["AHA_ID"].astype(str))].dropna()
        stab_durs = row[row.index.isin(stabilization["AHA_ID"].astype(str))].dropna()
        t_dir = def_durs.min() if len(def_durs) else float("inf")
        t_stab = stab_durs.min() if len(stab_durs) else float("inf")
        t_trans = t_stab + tau + (def_durs.min() if len(def_durs) else float("inf"))
        t_sys = min(t_dir, t_trans)
        delta = max(0.0, t_stab - stab_thresh)
        pathway = "transfer" if t_trans <= t_dir else "direct"
        idx = out[out[key_col].astype(str) == str(oid)].index[0]
        out.loc[idx, "t_dir"] = t_dir
        out.loc[idx, "t_stab"] = t_stab
        out.loc[idx, "t_trans"] = t_trans
        out.loc[idx, "t_sys"] = t_sys
        out.loc[idx, "t_delta"] = delta
        out.loc[idx, "access_pathway"] = pathway
    return out
