"""
Population-weighted aggregation of BEI and components to county and state levels.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import config
from .presentation_scope import DatasetProfile, get_profile

LOG = logging.getLogger(__name__)


def aggregate_to_county(tract_df: pd.DataFrame, pop_col: str = "total_pop") -> pd.DataFrame:
    """Roll up tract-level BEI/components and optional SVI to county (5-digit FIPS) with pop-weighted mean."""
    if "GEOID" not in tract_df.columns:
        return pd.DataFrame()
    out = tract_df.copy()
    out["county_fips"] = out["GEOID"].astype(str).str[:5]
    pop = out.groupby("county_fips")[pop_col].sum()
    cols = [c for c in ("bei", "s_score", "t_score", "p_score", "c_score") if c in out.columns]
    svi_cols = [c for c in ("svi_overall", "svi_theme1", "svi_theme2", "svi_theme3", "svi_theme4") if c in out.columns]
    cols = cols + svi_cols
    if not cols:
        return out.groupby("county_fips").agg({pop_col: "sum"}).reset_index()
    agg = out.groupby("county_fips").apply(lambda g: (g[cols].T * g[pop_col]).T.sum() / g[pop_col].sum() if g[pop_col].sum() > 0 else g[cols].mean(), include_groups=False)
    agg[pop_col] = pop
    return agg.reset_index()


def aggregate_to_state(tract_df: pd.DataFrame, pop_col: str = "total_pop") -> pd.DataFrame:
    """Roll up tract-level BEI/components and optional SVI to state (2-digit FIPS) with pop-weighted mean."""
    if "GEOID" not in tract_df.columns:
        return pd.DataFrame()
    out = tract_df.copy()
    out["state_fips"] = out["GEOID"].astype(str).str[:2]
    pop = out.groupby("state_fips")[pop_col].sum()
    cols = [c for c in ("bei", "s_score", "t_score", "p_score", "c_score") if c in out.columns]
    svi_cols = [c for c in ("svi_overall", "svi_theme1", "svi_theme2", "svi_theme3", "svi_theme4") if c in out.columns]
    cols = cols + svi_cols
    if not cols:
        return out.groupby("state_fips").agg({pop_col: "sum"}).reset_index()
    agg = out.groupby("state_fips").apply(lambda g: (g[cols].T * g[pop_col]).T.sum() / g[pop_col].sum() if g[pop_col].sum() > 0 else g[cols].mean(), include_groups=False)
    agg[pop_col] = pop
    return agg.reset_index()


def county_origins_from_tracts(tract_df: pd.DataFrame, pop_col: str = "total_pop") -> pd.DataFrame:
    """Derive county-level origins (centroids + denominators) from tract analytic table.

    This is the canonical builder for `usa_low_detail_county` routing origins.
    """
    required = {"GEOID", "centroid_lat", "centroid_lon", pop_col}
    missing = required - set(tract_df.columns)
    if missing:
        raise ValueError(f"Tract analytic table missing required columns for county origins: {sorted(missing)}")

    df = tract_df.copy()
    df["county_fips"] = df["GEOID"].astype(str).str[:5]
    df["state_fips"] = df["GEOID"].astype(str).str[:2]

    svi_cols = [c for c in ("svi_overall", "svi_theme1", "svi_theme2", "svi_theme3", "svi_theme4") if c in df.columns]

    def _weighted_centroid(group: pd.DataFrame) -> pd.Series:
        total_pop = group[pop_col].sum()
        if total_pop <= 0:
            lat = group["centroid_lat"].mean()
            lon = group["centroid_lon"].mean()
        else:
            lat = (group["centroid_lat"] * group[pop_col]).sum() / total_pop
            lon = (group["centroid_lon"] * group[pop_col]).sum() / total_pop
        out = {
            "state_fips": group["state_fips"].iloc[0],
            "centroid_lat": lat,
            "centroid_lon": lon,
            pop_col: total_pop,
        }
        if "child_pop" in group.columns:
            out["child_pop"] = group["child_pop"].sum()
        for sc in svi_cols:
            if total_pop > 0 and (group[sc].notna() & (group[pop_col] > 0)).any():
                out[sc] = (group[sc].fillna(0) * group[pop_col]).sum() / total_pop
            else:
                out[sc] = group[sc].mean()
        return pd.Series(out)

    county_df = df.groupby("county_fips", as_index=False).apply(_weighted_centroid, include_groups=False)
    # Optional: county_name if present on tracts (carry first non-null).
    if "county_name" in df.columns:
        names = (
            df[["county_fips", "county_name"]]
            .dropna(subset=["county_name"])
            .drop_duplicates(subset=["county_fips"])
        )
        county_df = county_df.merge(names, on="county_fips", how="left")
    return county_df


def build_county_analytic_table(
    tract_df: pd.DataFrame,
    pop_col: str = "total_pop",
) -> pd.DataFrame:
    """Build county-level analytic table from tract-level inputs.

    Aggregates tracts to counties: population-weighted centroid, summed total_pop
    and child_pop, and optional RUCA-derived is_rural (majority of county pop
    in rural tracts). Use for county-level analytics and as input to
    county_origins_from_tracts when you need a full county table; for routing
    origins only, county_origins_from_tracts(tract_df) is sufficient.
    """
    required = {"GEOID", "centroid_lat", "centroid_lon", pop_col}
    missing = required - set(tract_df.columns)
    if missing:
        raise ValueError(f"Tract table missing required columns for county derivation: {sorted(missing)}")

    county_df = county_origins_from_tracts(tract_df, pop_col=pop_col)
    if "ruca_code" in tract_df.columns and "is_rural" in tract_df.columns:
        df = tract_df.copy()
        df["county_fips"] = df["GEOID"].astype(str).str[:5]
        total = df.groupby("county_fips", as_index=False)[pop_col].sum()
        rural_pop = (
            df.loc[df["is_rural"].fillna(False)]
            .groupby("county_fips", as_index=False)[pop_col]
            .sum()
            .rename(columns={pop_col: "rural_pop"})
        )
        total = total.merge(rural_pop, on="county_fips", how="left")
        total["rural_pop"] = total["rural_pop"].fillna(0)
        total["is_rural"] = total["rural_pop"] > (total[pop_col] * 0.5)
        county_df = county_df.merge(
            total[["county_fips", "is_rural"]], on="county_fips", how="left"
        )
    else:
        county_df["is_rural"] = False
    return county_df


def aggregate_air_delta_to_county(
    delta_df: pd.DataFrame,
    tract_df: pd.DataFrame | None = None,
    pop_col: str = "total_pop",
) -> pd.DataFrame:
    """Roll up tract-level air-scenario deltas to county (5-digit FIPS).

    Expects ``delta_df`` from :func:`~.bei_composite.compute_scenario_delta` with
    columns: tract_geoid, bei_ground, bei_air, bei_delta, t_sys_ground, t_sys_air,
    t_delta, air_feasible, air_materially_helps. If ``tract_df`` is provided with
    GEOID and ``pop_col``, aggregation uses population-weighted means; otherwise
    uses simple means per county.

    Returns
    -------
    DataFrame
        One row per county with county_fips and aggregated delta columns
        (e.g. bei_ground, bei_air, bei_delta, t_sys_ground, t_sys_air, t_delta,
        air_feasible, air_materially_helps). When tract_df is provided, also
        includes total population (pop_col) for the county.
    """
    if "tract_geoid" not in delta_df.columns:
        return pd.DataFrame()
    out = delta_df.copy()
    out["county_fips"] = out["tract_geoid"].astype(str).str[:5]

    numeric_cols = [c for c in ("bei_ground", "bei_air", "bei_delta", "t_sys_ground", "t_sys_air", "t_delta") if c in out.columns]
    bool_cols = [c for c in ("air_feasible", "air_materially_helps") if c in out.columns]
    agg_cols = numeric_cols + bool_cols
    if not agg_cols:
        return out.groupby("county_fips", as_index=False).first()

    if tract_df is not None and "GEOID" in tract_df.columns and pop_col in tract_df.columns:
        out = out.merge(
            tract_df[["GEOID", pop_col]].rename(columns={"GEOID": "tract_geoid"}),
            on="tract_geoid",
            how="left",
        )
        out[pop_col] = out[pop_col].fillna(0)

        def _weighted(g: pd.DataFrame) -> pd.Series:
            total_pop = g[pop_col].sum()
            if total_pop <= 0:
                ser = g[agg_cols].mean()
                ser[pop_col] = 0.0
                return ser
            ser = pd.Series(
                [(g[c].astype(float) * g[pop_col]).sum() / total_pop for c in agg_cols],
                index=agg_cols,
            )
            ser[pop_col] = total_pop
            return ser

        agg = out.groupby("county_fips", as_index=False).apply(_weighted, include_groups=False)
        agg = agg.reset_index()
    else:
        agg = out.groupby("county_fips", as_index=False)[agg_cols].mean()

    return agg


def county_aggregation_paths(profile: DatasetProfile | None = None) -> dict[str, Path]:
    """Return canonical output paths for county-level national aggregates.

    These conventions are used for the `usa_low_detail_county` profile, but
    are generic enough for any national, county-only presentation profile.
    """
    prof = profile or get_profile()
    prefix = prof.output_prefix
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    config.GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "county_access_table": config.TABLES_DIR / f"{prefix}_county_access.parquet",
        "county_bei_table": config.TABLES_DIR / f"{prefix}_county_bei.parquet",
        "county_bei_geojson": config.GEOJSON_DIR / f"{prefix}_county_bei.geojson",
    }


def validate_county_only_profile(profile: DatasetProfile) -> None:
    """Lightweight validation for county-only national presentation profiles."""
    if profile.scope_level != "national":
        raise ValueError(
            f"County-only presentation profile '{profile.profile_id}' must have "
            f"scope_level='national', got {profile.scope_level!r}"
        )
    if profile.origin_state_fips:
        LOG.warning(
            "County-only profile '%s' has origin_state_fips set; national runs "
            "are expected to cover all states. This may be intentional but is "
            "worth double-checking.",
            profile.profile_id,
        )
