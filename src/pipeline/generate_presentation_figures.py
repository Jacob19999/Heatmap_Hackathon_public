"""
Generate all presentation-ready Challenge Area 3 figures from real pipeline data.

Reads computed Valhalla-routed access/BEI data, fixes inf values, recomputes
BEI with all four pillars, and produces story-driven visuals for MN (high detail)
and USA (low detail).

Usage:
    python -m src.pipeline.generate_presentation_figures
"""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
import contextily as ctx
from pyproj import Transformer

# Coordinate transformer: WGS84 lon/lat → Web Mercator (EPSG:3857)
_WGS84_TO_MERC = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

# MN map extent in WGS84 → converted to Web Mercator for basemap
_MN_LON_MIN, _MN_LON_MAX = -97.5, -89.0
_MN_LAT_MIN, _MN_LAT_MAX = 43.0, 49.5
_MN_XMIN, _MN_YMIN = _WGS84_TO_MERC.transform(_MN_LON_MIN, _MN_LAT_MIN)
_MN_XMAX, _MN_YMAX = _WGS84_TO_MERC.transform(_MN_LON_MAX, _MN_LAT_MAX)


def _to_merc(lons, lats):
    """Convert arrays of WGS84 lon/lat to Web Mercator x/y."""
    x, y = _WGS84_TO_MERC.transform(np.asarray(lons), np.asarray(lats))
    return x, y


def _add_basemap(ax):
    """Add a clean, light CartoDB Positron basemap to a Web Mercator axis."""
    try:
        ctx.add_basemap(
            ax,
            crs="EPSG:3857",
            source=ctx.providers.CartoDB.Positron,
            zoom="auto",
            attribution=False,
        )
    except Exception:
        # Fallback: no tiles (e.g. offline)
        ax.set_facecolor("#EEF2F6")

from . import config
from .bei_components import robust_norm, step_decay, gap_score

LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
PALETTE = {
    "primary": "#1B2838",
    "accent": "#E85D04",
    "rural": "#D62828",
    "urban": "#457B9D",
    "transfer": "#F4A261",
    "direct": "#2A9D8F",
    "pediatric": "#E76F51",
    "adult": "#264653",
    "supply": "#E9C46A",
    "access": "#E76F51",
    "peds": "#F4A261",
    "capacity": "#264653",
    "bei_low": "#FFF3B0",
    "bei_high": "#9D0208",
    "bg": "#FAFBFC",
    "grid": "#E0E4E8",
    "text": "#1B2838",
    "muted": "#6C757D",
}
BEI_CMAP = "YlOrRd"
FIGSIZE_WIDE = (14, 7)
FIGSIZE_MAP = (12, 10)
FIGSIZE_SQUARE = (10, 8)
DPI = 200

INF_CAP_MIN = 480.0  # 8 hours: cap for unreachable tracts


def _style_ax(ax, title: str, subtitle: str = "", xlabel: str = "", ylabel: str = ""):
    ax.set_facecolor(PALETTE["bg"])
    ax.set_title(title, fontsize=16, fontweight="bold", color=PALETTE["text"], pad=12, loc="left")
    if subtitle:
        ax.text(0.0, 1.08, subtitle, transform=ax.transAxes, fontsize=10,
                color=PALETTE["muted"], va="bottom", ha="left")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11, color=PALETTE["text"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11, color=PALETTE["text"])
    ax.tick_params(colors=PALETTE["text"], labelsize=9)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.5, alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PALETTE["grid"])
    ax.spines["bottom"].set_color(PALETTE["grid"])


def _annotate_bar(ax, bars, fmt="{:.0f}"):
    for bar in bars:
        h = bar.get_height()
        if np.isfinite(h) and h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h, fmt.format(h),
                    ha="center", va="bottom", fontsize=8, color=PALETTE["text"])


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close(fig)
    LOG.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_mn_access() -> pd.DataFrame:
    p = config.TABLES_DIR / "mn_high_detail_tract_access.parquet"
    if not p.exists():
        p = config.TABLES_DIR / "mn_mvp_tract_access.parquet"
    df = pd.read_parquet(p)
    for col in ("t_dir", "t_stab", "t_trans", "t_sys"):
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], INF_CAP_MIN)
    return df


def _load_mn_bei() -> pd.DataFrame:
    p = config.TABLES_DIR / "mn_high_detail_tract_bei.parquet"
    if not p.exists():
        p = config.TABLES_DIR / "mn_mvp_tract_bei.parquet"
    df = pd.read_parquet(p)
    for col in ("t_dir", "t_stab", "t_trans", "t_sys"):
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], INF_CAP_MIN)
    return df


def _load_usa_access() -> pd.DataFrame:
    p = config.TABLES_DIR / "usa_low_detail_county_county_access.parquet"
    df = pd.read_parquet(p)
    for col in ("t_dir", "t_stab", "t_trans", "t_sys"):
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], INF_CAP_MIN)
    return df


def _load_usa_bei() -> pd.DataFrame:
    p = config.TABLES_DIR / "usa_low_detail_county_county_bei.parquet"
    df = pd.read_parquet(p)
    for col in ("t_dir", "t_stab", "t_trans", "t_sys"):
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], INF_CAP_MIN)
    return df


def _load_facilities() -> pd.DataFrame:
    return pd.read_parquet(config.REPO_ROOT / "Data" / "processed" / "facilities_geo.parquet")


def _load_tract_denoms() -> pd.DataFrame:
    return pd.read_parquet(config.REPO_ROOT / "Data" / "processed" / "tract_denominators.parquet")


def _load_mn_matrix() -> pd.DataFrame:
    """Load the MN travel-time matrix (filled if available)."""
    filled = config.REPO_ROOT / "Data" / "output" / "Travel Dist Processed" / "valhalla_mn_hospitals_timedist_filled.parquet"
    raw = config.TABLES_DIR / "valhalla_mn_hospitals_timedist.parquet"
    p = filled if filled.exists() else raw
    m = pd.read_parquet(p)
    if "duration_min_filled" in m.columns:
        m["duration_min"] = m["duration_min_filled"]
    m["origin_id"] = m["origin_id"].astype(str)
    m["destination_id"] = m["destination_id"].astype(str)
    m["duration_min"] = m["duration_min"].replace([np.inf, -np.inf], INF_CAP_MIN)
    return m


def _recompute_bei(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute BEI with all four pillars derived from the travel-time matrix."""
    out = df.copy()
    out["t_score"] = robust_norm(out["t_sys"])

    matrix = _load_mn_matrix()
    _compute_supply_from_matrix(out, matrix)
    _compute_peds_from_matrix(out, matrix)
    _compute_capacity_from_matrix(out, matrix)

    w = config.BEI_WEIGHTS
    out["bei"] = 100.0 * (
        w[0] * out["s_score"] + w[1] * out["t_score"] +
        w[2] * out["p_score"] + w[3] * out["c_score"]
    )
    out["bei_percentile"] = out["bei"].rank(pct=True) * 100
    return out


def _compute_supply_from_matrix(df: pd.DataFrame, matrix: pd.DataFrame):
    """S score: count of reachable burn centers from travel-time matrix, weighted by step-decay."""
    key = "GEOID" if "GEOID" in df.columns else "tract_geoid"
    pivot = matrix.pivot_table(index="origin_id", columns="destination_id",
                                values="duration_min", aggfunc="first")
    supply_vals = []
    for _, row in df.iterrows():
        oid = str(row[key])
        if oid in pivot.index:
            times = pivot.loc[oid].dropna()
            w = step_decay(times.values)
            supply_vals.append(w.sum())
        else:
            supply_vals.append(0.0)
    df["supply_accessibility"] = supply_vals
    df["s_score"] = gap_score(np.array(supply_vals))


def _compute_peds_from_matrix(df: pd.DataFrame, matrix: pd.DataFrame):
    """P score: proxy pediatric access. Pediatric-capable centers are rarer,
    so we use the 3rd-nearest center time as a proxy for pediatric travel."""
    key = "GEOID" if "GEOID" in df.columns else "tract_geoid"
    pivot = matrix.pivot_table(index="origin_id", columns="destination_id",
                                values="duration_min", aggfunc="first")
    peds_vals = []
    for _, row in df.iterrows():
        oid = str(row[key])
        if oid in pivot.index:
            times = pivot.loc[oid].dropna().sort_values()
            if len(times) >= 3:
                peds_vals.append(times.iloc[2])
            elif len(times) >= 1:
                peds_vals.append(times.iloc[-1] * 1.3)
            else:
                peds_vals.append(INF_CAP_MIN)
        else:
            peds_vals.append(INF_CAP_MIN)
    df["peds_travel_proxy"] = peds_vals
    df["p_score"] = robust_norm(np.array(peds_vals))


def _compute_capacity_from_matrix(df: pd.DataFrame, matrix: pd.DataFrame):
    """C score: decay-weighted hospital count. More accessible hospitals = more structural capacity."""
    key = "GEOID" if "GEOID" in df.columns else "tract_geoid"
    pivot = matrix.pivot_table(index="origin_id", columns="destination_id",
                                values="duration_min", aggfunc="first")
    cap_vals = []
    for _, row in df.iterrows():
        oid = str(row[key])
        if oid in pivot.index:
            times = pivot.loc[oid].dropna()
            w = step_decay(times.values)
            cap_vals.append((w > 0).sum() + w.sum() * 0.5)
        else:
            cap_vals.append(0.0)
    df["capacity_accessibility"] = cap_vals
    df["c_score"] = gap_score(np.array(cap_vals))


def _haversine_km_vec(lat1, lon1, lat2, lon2):
    """Vectorized haversine distance in km."""
    R = 6371
    a = np.radians(lat2 - lat1)
    b = np.radians(lon2 - lon1)
    x = np.sin(a / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(b / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(x, 0, 1)))


def _compute_supply_score_catchment(df: pd.DataFrame, fac: pd.DataFrame):
    """S score: step-decay-weighted count of burn centers accessible from each tract.

    Uses haversine distance as proxy for drive time (km / 0.8 ≈ minutes).
    Higher score = worse (fewer centers nearby).
    """
    lat_col = "latitude" if "latitude" in fac.columns else "centroid_lat"
    lon_col = "longitude" if "longitude" in fac.columns else "centroid_lon"
    valid_fac = fac[fac[lat_col].notna() & fac[lon_col].notna()].copy()
    burn_fac = valid_fac[valid_fac["supply_weight"] > 0] if "supply_weight" in valid_fac.columns else valid_fac

    if len(burn_fac) == 0 or "centroid_lat" not in df.columns:
        df["s_score"] = 0.5
        return

    fac_lats = burn_fac[lat_col].values
    fac_lons = burn_fac[lon_col].values
    fac_weights = burn_fac["supply_weight"].values if "supply_weight" in burn_fac.columns else np.ones(len(burn_fac))

    supply_accessibility = np.zeros(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        dists_km = _haversine_km_vec(row["centroid_lat"], row["centroid_lon"], fac_lats, fac_lons)
        travel_proxy = dists_km / 0.8
        weights = step_decay(travel_proxy)
        supply_accessibility[i] = (weights * fac_weights).sum()

    df["supply_accessibility"] = supply_accessibility
    df["s_score"] = gap_score(supply_accessibility)


def _compute_peds_score_catchment(df: pd.DataFrame, fac: pd.DataFrame):
    """P score: pediatric access based on haversine distance to nearest pediatric-capable center."""
    peds_col = None
    for col_name in ["BURN_PEDS", "burn_peds"]:
        if col_name in fac.columns:
            peds_col = col_name
            break

    lat_col = "latitude" if "latitude" in fac.columns else "centroid_lat"
    lon_col = "longitude" if "longitude" in fac.columns else "centroid_lon"

    if peds_col is not None:
        peds_fac = fac[(fac[peds_col] == 1) | (fac[peds_col] == True)]
        peds_fac = peds_fac[peds_fac[lat_col].notna() & peds_fac[lon_col].notna()]
    else:
        peds_fac = pd.DataFrame()

    if len(peds_fac) == 0 or "centroid_lat" not in df.columns:
        df["peds_travel_min"] = df["t_sys"] * 1.3
        df["p_score"] = robust_norm(df["peds_travel_min"])
        return

    fac_lats = peds_fac[lat_col].values
    fac_lons = peds_fac[lon_col].values

    peds_times = np.zeros(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        dists_km = _haversine_km_vec(row["centroid_lat"], row["centroid_lon"], fac_lats, fac_lons)
        peds_times[i] = dists_km.min() / 0.8

    df["peds_travel_min"] = peds_times
    df["p_score"] = robust_norm(peds_times)


def _compute_capacity_score_catchment(df: pd.DataFrame, fac: pd.DataFrame):
    """C score: step-decay-weighted burn bed availability per tract.

    Sums burn beds at all facilities weighted by step_decay of haversine distance.
    """
    lat_col = "latitude" if "latitude" in fac.columns else "centroid_lat"
    lon_col = "longitude" if "longitude" in fac.columns else "centroid_lon"
    bed_col = "BURN_BEDS" if "BURN_BEDS" in fac.columns else "burn_beds"

    valid_fac = fac[fac[lat_col].notna() & fac[lon_col].notna()].copy()
    valid_fac[bed_col] = pd.to_numeric(valid_fac[bed_col], errors="coerce").fillna(0)

    if len(valid_fac) == 0 or "centroid_lat" not in df.columns:
        df["c_score"] = 0.5
        return

    fac_lats = valid_fac[lat_col].values
    fac_lons = valid_fac[lon_col].values
    fac_beds = valid_fac[bed_col].values

    bed_accessibility = np.zeros(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        dists_km = _haversine_km_vec(row["centroid_lat"], row["centroid_lon"], fac_lats, fac_lons)
        travel_proxy = dists_km / 0.8
        weights = step_decay(travel_proxy)
        bed_accessibility[i] = (weights * fac_beds).sum()

    df["bed_accessibility"] = bed_accessibility
    df["c_score"] = gap_score(bed_accessibility)


# ---------------------------------------------------------------------------
# MN figures (high detail)
# ---------------------------------------------------------------------------

def fig_mn_01_burn_center_map(out_dir: Path) -> Path:
    """MN burn center locations sized by bed count, colored by verification status."""
    fac = _load_facilities()
    mn_fac = fac[fac["state_fips"].isin(["27", "38", "46", "19", "55"])].copy()
    mn_acc = _load_mn_access()

    fig, ax = plt.subplots(figsize=FIGSIZE_MAP, facecolor="white")

    # Plot tract centroids as faint context dots (Web Mercator)
    if "centroid_lat" in mn_acc.columns:
        cx, cy = _to_merc(mn_acc["centroid_lon"], mn_acc["centroid_lat"])
        ax.scatter(cx, cy, c="#B0B8C4", s=1, alpha=0.25, zorder=2)

    bed_col = "BURN_BEDS" if "BURN_BEDS" in mn_fac.columns else "burn_beds"
    lat_col = "latitude" if "latitude" in mn_fac.columns else "centroid_lat"
    lon_col = "longitude" if "longitude" in mn_fac.columns else "centroid_lon"

    valid = mn_fac[mn_fac[lat_col].notna() & mn_fac[lon_col].notna()].copy()
    is_aba = valid.get("ABA_VERIFIED", pd.Series(False, index=valid.index)).astype(bool)
    sizes = valid[bed_col].clip(lower=1).fillna(1) * 8

    vx, vy = _to_merc(valid[lon_col], valid[lat_col])
    valid = valid.copy()
    valid["_x"] = vx
    valid["_y"] = vy

    non_aba = valid[~is_aba]
    aba = valid[is_aba]
    if len(non_aba) > 0:
        ax.scatter(non_aba["_x"], non_aba["_y"],
                   s=sizes[~is_aba], c=PALETTE["urban"], alpha=0.8,
                   edgecolors="white", linewidth=0.8, zorder=4, label="Non-ABA Verified")
    if len(aba) > 0:
        ax.scatter(aba["_x"], aba["_y"],
                   s=sizes[is_aba], c=PALETTE["accent"], alpha=0.95,
                   edgecolors="white", linewidth=1.0, zorder=5, label="ABA Verified")

    ax.set_xlim(_MN_XMIN, _MN_XMAX)
    ax.set_ylim(_MN_YMIN, _MN_YMAX)
    _add_basemap(ax)
    ax.set_axis_off()

    n_total = len(valid)
    n_aba = is_aba.sum()
    n_beds = valid[bed_col].sum()
    ax.set_title(
        "Where Are the Burn Centers?",
        fontsize=18, fontweight="bold", color=PALETTE["text"], pad=20, loc="left"
    )
    ax.text(0.0, 1.01,
            f"Minnesota & neighbors: {n_total} centers, {n_aba} ABA-verified, {n_beds:.0f} burn beds",
            transform=ax.transAxes, fontsize=11, color=PALETTE["muted"], va="bottom")
    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)

    path = out_dir / "mn_01_burn_center_map.png"
    _save(fig, path)
    return path


def fig_mn_02_travel_time_map(out_dir: Path) -> Path:
    """Choropleth-style scatter of MN tracts colored by travel time to nearest burn center."""
    df = _load_mn_access()
    finite = df[np.isfinite(df["t_sys"])].copy()

    fig, ax = plt.subplots(figsize=FIGSIZE_MAP, facecolor="white")

    # Project tract centroids to Web Mercator
    fx, fy = _to_merc(finite["centroid_lon"], finite["centroid_lat"])
    t_capped = finite["t_sys"].clip(upper=240)

    sc = ax.scatter(
        fx, fy,
        c=t_capped, s=7, cmap="RdYlGn_r", vmin=0, vmax=240,
        edgecolors="none", alpha=0.85, zorder=3
    )
    cbar = plt.colorbar(sc, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Minutes to Nearest Burn Center", fontsize=10)

    ax.set_xlim(_MN_XMIN, _MN_XMAX)
    ax.set_ylim(_MN_YMIN, _MN_YMAX)
    _add_basemap(ax)
    ax.set_axis_off()

    median_t = finite["t_sys"].median()
    pct_over_60 = (finite["t_sys"] > 60).sum() / len(finite) * 100
    ax.set_title(
        "Ground Travel Time to Nearest Burn Center",
        fontsize=18, fontweight="bold", color=PALETTE["text"], pad=20, loc="left"
    )
    ax.text(0.0, 1.01,
            f"Median: {median_t:.0f} min  |  {pct_over_60:.0f}% of tracts > 60 min",
            transform=ax.transAxes, fontsize=11, color=PALETTE["muted"], va="bottom")

    path = out_dir / "mn_02_travel_time_map.png"
    _save(fig, path)
    return path


def fig_mn_03_rural_urban_gap(out_dir: Path) -> Path:
    """Rural vs urban travel time distributions."""
    df = _load_mn_access()
    finite = df[np.isfinite(df["t_sys"])].copy()
    if "is_rural" not in finite.columns:
        finite["is_rural"] = False

    rural = finite[finite["is_rural"]]["t_sys"]
    urban = finite[~finite["is_rural"]]["t_sys"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE, facecolor="white",
                                    gridspec_kw={"width_ratios": [2, 1]})

    bins = np.arange(0, 300, 10)
    ax1.hist(urban, bins=bins, alpha=0.7, color=PALETTE["urban"], label=f"Urban (n={len(urban):,})", density=True)
    ax1.hist(rural, bins=bins, alpha=0.7, color=PALETTE["rural"], label=f"Rural (n={len(rural):,})", density=True)
    ax1.axvline(urban.median(), color=PALETTE["urban"], linestyle="--", linewidth=2, alpha=0.8)
    ax1.axvline(rural.median(), color=PALETTE["rural"], linestyle="--", linewidth=2, alpha=0.8)
    ax1.text(urban.median() + 3, ax1.get_ylim()[1] * 0.85, f"Median\n{urban.median():.0f} min",
             color=PALETTE["urban"], fontsize=9, fontweight="bold")
    ax1.text(rural.median() + 3, ax1.get_ylim()[1] * 0.70, f"Median\n{rural.median():.0f} min",
             color=PALETTE["rural"], fontsize=9, fontweight="bold")
    _style_ax(ax1, "Travel Time Distribution", xlabel="Minutes to Nearest Burn Center", ylabel="Density")
    ax1.legend(fontsize=10, framealpha=0.9)

    categories = ["Urban", "Rural"]
    medians = [urban.median(), rural.median()]
    means = [urban.mean(), rural.mean()]
    pct_over_60 = [(urban > 60).mean() * 100, (rural > 60).mean() * 100]

    x = np.arange(len(categories))
    bars = ax2.bar(x, medians, width=0.35, color=[PALETTE["urban"], PALETTE["rural"]], alpha=0.85)
    _annotate_bar(ax2, bars)
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    _style_ax(ax2, "Median Travel Time", ylabel="Minutes")

    for i, (cat, pct) in enumerate(zip(categories, pct_over_60)):
        ax2.text(i, medians[i] * 0.5, f"{pct:.0f}% > 60 min",
                 ha="center", fontsize=9, color="white", fontweight="bold")

    gap = rural.median() - urban.median()
    fig.suptitle("The Rural–Urban Burn Access Divide",
                 fontsize=18, fontweight="bold", color=PALETTE["text"], y=0.97)
    fig.text(0.5, 0.91,
             f"Rural Minnesotans travel {gap:.0f} minutes longer on average to reach a burn center",
             ha="center", fontsize=11, color=PALETTE["muted"])

    fig.tight_layout(rect=[0, 0, 1, 0.89])
    path = out_dir / "mn_03_rural_urban_gap.png"
    _save(fig, path)
    return path


def fig_mn_04_coverage_curve(out_dir: Path) -> Path:
    """Cumulative population coverage by drive time."""
    df = _load_mn_access()
    finite = df[np.isfinite(df["t_sys"])].copy()
    total_pop = finite["total_pop"].sum()

    thresholds = np.arange(0, 301, 5)
    pop_covered = []
    for t in thresholds:
        covered = finite.loc[finite["t_sys"] <= t, "total_pop"].sum()
        pop_covered.append(covered / total_pop * 100 if total_pop > 0 else 0)

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE, facecolor="white")

    ax.fill_between(thresholds, pop_covered, alpha=0.15, color=PALETTE["accent"])
    ax.plot(thresholds, pop_covered, color=PALETTE["accent"], linewidth=2.5)

    key_thresholds = [30, 60, 90, 120, 180]
    for t in key_thresholds:
        idx = t // 5
        if idx < len(pop_covered):
            pct = pop_covered[idx]
            ax.plot(t, pct, "o", color=PALETTE["accent"], markersize=8, zorder=5)
            ax.annotate(f"{pct:.0f}% at {t} min",
                        xy=(t, pct), xytext=(t + 8, pct - 3),
                        fontsize=9, color=PALETTE["text"],
                        arrowprops=dict(arrowstyle="-", color=PALETTE["muted"], lw=0.8))

    ax.axhline(90, color=PALETTE["grid"], linestyle=":", linewidth=1)
    ax.text(5, 91, "90% coverage target", fontsize=9, color=PALETTE["muted"])

    _style_ax(ax, "Population Coverage by Drive Time",
              subtitle=f"Total MN population: {total_pop:,.0f}",
              xlabel="Maximum Drive Time (minutes)",
              ylabel="% Population Covered")
    ax.set_xlim(0, 300)
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())

    fig.tight_layout()
    path = out_dir / "mn_04_coverage_curve.png"
    _save(fig, path)
    return path


def fig_mn_05_access_pathway(out_dir: Path) -> Path:
    """Direct vs transfer pathway comparison."""
    df = _load_mn_access()
    finite = df[np.isfinite(df["t_sys"])].copy()

    direct = finite[finite["access_pathway"] == "direct"]
    transfer = finite[finite["access_pathway"] == "transfer"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE, facecolor="white",
                                    gridspec_kw={"width_ratios": [1.5, 1]})

    if "centroid_lat" in finite.columns:
        colors = finite["access_pathway"].map({"direct": PALETTE["direct"], "transfer": PALETTE["transfer"]})
        ax1.scatter(finite["centroid_lon"], finite["centroid_lat"],
                    c=colors, s=6, alpha=0.7, zorder=2)
        ax1.set_xlim(-97.5, -89)
        ax1.set_ylim(43, 49.5)
        ax1.set_axis_off()
        ax1.set_title("Access Pathway by Tract", fontsize=14, fontweight="bold",
                       color=PALETTE["text"], pad=12, loc="left")
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=PALETTE["direct"], label=f"Direct ({len(direct):,} tracts)"),
            Patch(facecolor=PALETTE["transfer"], label=f"Transfer ({len(transfer):,} tracts)")
        ]
        ax1.legend(handles=legend_elements, loc="lower right", fontsize=10, framealpha=0.9)

    categories = ["Direct\nAccess", "Stabilize +\nTransfer"]
    vals = [direct["t_sys"].median() if len(direct) else 0,
            transfer["t_sys"].median() if len(transfer) else 0]
    bars = ax2.bar(categories, vals, color=[PALETTE["direct"], PALETTE["transfer"]], width=0.5)
    _annotate_bar(ax2, bars)

    if len(transfer) > 0 and len(direct) > 0:
        penalty = transfer["t_sys"].median() - direct["t_sys"].median()
        ax2.annotate(f"+{penalty:.0f} min\ntransfer penalty",
                     xy=(1, vals[1]), xytext=(1.3, vals[1] * 0.7),
                     fontsize=10, color=PALETTE["accent"], fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color=PALETTE["accent"]))

    _style_ax(ax2, "Median System Time", ylabel="Minutes")

    fig.suptitle("Direct vs Transfer Access Pathways",
                 fontsize=18, fontweight="bold", color=PALETTE["text"], y=0.97)
    n_transfer = len(transfer)
    pct_transfer = n_transfer / len(finite) * 100 if len(finite) > 0 else 0
    fig.text(0.5, 0.91,
             f"{pct_transfer:.0f}% of MN tracts rely on stabilize-and-transfer pathway",
             ha="center", fontsize=11, color=PALETTE["muted"])

    fig.tight_layout(rect=[0, 0, 1, 0.89])
    path = out_dir / "mn_05_access_pathway.png"
    _save(fig, path)
    return path


def fig_mn_06_bei_map(out_dir: Path) -> Path:
    """BEI composite map of MN tracts with physical basemap."""
    df = _load_mn_access()
    bei = _recompute_bei(df)

    # Project tract centroids to Web Mercator
    bx, by = _to_merc(bei["centroid_lon"].values, bei["centroid_lat"].values)

    fig, ax = plt.subplots(figsize=FIGSIZE_MAP, facecolor="white")

    sc = ax.scatter(
        bx, by,
        c=bei["bei"], s=8, cmap=BEI_CMAP, vmin=0, vmax=100,
        edgecolors="none", alpha=0.85, zorder=3
    )
    cbar = plt.colorbar(sc, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Burn Equity Index (0–100, higher = more inequitable)", fontsize=10)

    fac = _load_facilities()
    mn_fac = fac[fac["state_fips"].isin(["27", "38", "46", "19", "55"])]
    lat_col = "latitude" if "latitude" in mn_fac.columns else "centroid_lat"
    lon_col = "longitude" if "longitude" in mn_fac.columns else "centroid_lon"
    valid_fac = mn_fac[mn_fac[lat_col].notna()]
    fx, fy = _to_merc(valid_fac[lon_col].values, valid_fac[lat_col].values)
    ax.scatter(fx, fy,
               marker="P", c="white", edgecolors=PALETTE["primary"],
               s=60, linewidth=1.2, zorder=5, label="Burn Centers")

    top10 = bei.nlargest(10, "bei")
    for _, row in top10.iterrows():
        tx, ty = _to_merc([row["centroid_lon"]], [row["centroid_lat"]])
        ox, oy = _to_merc([row["centroid_lon"] + 0.15], [row["centroid_lat"] + 0.1])
        ax.annotate("", xy=(tx[0], ty[0]),
                     xytext=(ox[0], oy[0]),
                     arrowprops=dict(arrowstyle="->", color=PALETTE["bei_high"], lw=1.2))

    ax.set_xlim(_MN_XMIN, _MN_XMAX)
    ax.set_ylim(_MN_YMIN, _MN_YMAX)
    _add_basemap(ax)

    p90 = bei["bei"].quantile(0.9)
    hotspot_count = (bei["bei"] >= p90).sum()
    hotspot_pop = bei.loc[bei["bei"] >= p90, "total_pop"].sum()
    ax.set_title(
        "Burn Equity Index — Minnesota Tracts",
        fontsize=18, fontweight="bold", color=PALETTE["text"], pad=8, loc="left"
    )
    ax.text(0.0, 1.06,
            f"{hotspot_count} high-burden tracts (top 10%) affecting {hotspot_pop:,.0f} residents",
            transform=ax.transAxes, fontsize=11, color=PALETTE["muted"], va="bottom")

    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)
    ax.set_axis_off()
    path = out_dir / "mn_06_bei_map.png"
    _save(fig, path)

    bei.to_parquet(out_dir.parent / "tables" / "mn_bei_recomputed.parquet", index=False)
    return path


def fig_mn_07_bei_drivers(out_dir: Path) -> Path:
    """BEI pillar breakdown: what drives inequity in high-burden areas."""
    df = _load_mn_access()
    bei = _recompute_bei(df)

    p80 = bei["bei"].quantile(0.8)
    top = bei[bei["bei"] >= p80].copy()
    bottom = bei[bei["bei"] < bei["bei"].quantile(0.2)].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE, facecolor="white")

    pillars = ["Supply\nScarcity", "Travel\nBurden", "Pediatric\nGap", "Capacity\nScarcity"]
    top_means = [top["s_score"].mean(), top["t_score"].mean(),
                 top["p_score"].mean(), top["c_score"].mean()]
    bot_means = [bottom["s_score"].mean(), bottom["t_score"].mean(),
                 bottom["p_score"].mean(), bottom["c_score"].mean()]

    x = np.arange(len(pillars))
    w = 0.35
    bars1 = ax1.bar(x - w / 2, top_means, w, color=PALETTE["bei_high"],
                     alpha=0.85, label="High-burden tracts (top 20%)")
    bars2 = ax1.bar(x + w / 2, bot_means, w, color=PALETTE["urban"],
                     alpha=0.85, label="Low-burden tracts (bottom 20%)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(pillars)
    _style_ax(ax1, "BEI Pillar Scores", ylabel="Score (0–1, higher = worse)")
    ax1.legend(fontsize=9, framealpha=0.9)
    ax1.set_ylim(0, 1.1)

    weights = np.array(config.BEI_WEIGHTS)
    weighted_top = np.array(top_means) * weights
    colors = [PALETTE["supply"], PALETTE["access"], PALETTE["peds"], PALETTE["capacity"]]
    labels = ["Supply (25%)", "Access (30%)", "Pediatric (20%)", "Capacity (25%)"]
    ax2.pie(weighted_top, labels=labels, colors=colors, autopct="%1.0f%%",
            startangle=90, textprops={"fontsize": 10})
    ax2.set_title("Weighted Contribution in High-Burden Areas",
                   fontsize=14, fontweight="bold", color=PALETTE["text"], pad=12)

    fig.suptitle("What Drives Burn Equity Gaps?",
                 fontsize=18, fontweight="bold", color=PALETTE["text"], y=1.02)
    fig.tight_layout()
    path = out_dir / "mn_07_bei_drivers.png"
    _save(fig, path)
    return path


def fig_mn_08_hotspot_profile(out_dir: Path) -> Path:
    """Top 15 highest-BEI counties in MN with pillar breakdown."""
    import json
    df = _load_mn_access()
    bei = _recompute_bei(df)

    # Load county name lookup (3-digit COUNTYFP → "Aitkin County" etc.)
    cn_path = out_dir.parent / "dashboard" / "mn_county_names.json"
    if not cn_path.exists():
        cn_path = Path("outputs/dashboard/mn_county_names.json")
    county_names: dict = {}
    if cn_path.exists():
        county_names = json.loads(cn_path.read_text())

    # Aggregate to county level (population-weighted)
    w = config.BEI_WEIGHTS
    bei["county_fips"] = (
        bei["STATEFP"].astype(str).str.zfill(2)
        + bei["COUNTYFP"].astype(str).str.zfill(3)
    )
    county = (
        bei.groupby(["county_fips", "COUNTYFP"], group_keys=False)
        .apply(
            lambda g: pd.Series({
                "pop": g["total_pop"].sum(),
                "n_tracts": len(g),
                "bei": (g["bei"] * g["total_pop"]).sum() / g["total_pop"].sum()
                        if g["total_pop"].sum() > 0 else g["bei"].mean(),
                "s_score": (g["s_score"] * g["total_pop"]).sum() / g["total_pop"].sum()
                            if g["total_pop"].sum() > 0 else g["s_score"].mean(),
                "t_score": (g["t_score"] * g["total_pop"]).sum() / g["total_pop"].sum()
                            if g["total_pop"].sum() > 0 else g["t_score"].mean(),
                "p_score": (g["p_score"] * g["total_pop"]).sum() / g["total_pop"].sum()
                            if g["total_pop"].sum() > 0 else g["p_score"].mean(),
                "c_score": (g["c_score"] * g["total_pop"]).sum() / g["total_pop"].sum()
                            if g["total_pop"].sum() > 0 else g["c_score"].mean(),
                "pct_rural": g["is_rural"].mean() * 100,
            }), include_groups=False,
        )
        .reset_index()
    )
    county["county_name"] = (
        county["COUNTYFP"].astype(str).str.zfill(3)
        .map(county_names)
        .fillna(county["COUNTYFP"].astype(str).str.zfill(3) + " County")
    )
    # Shorten "X County" → "X" for cleaner labels
    county["label"] = county["county_name"].str.replace(" County", "", regex=False)
    top = county.nlargest(15, "bei").copy()

    fig, ax = plt.subplots(figsize=(14, 8), facecolor="white")

    y = np.arange(len(top))
    s_contrib = top["s_score"] * w[0] * 100
    t_contrib = top["t_score"] * w[1] * 100
    p_contrib = top["p_score"] * w[2] * 100
    c_contrib = top["c_score"] * w[3] * 100

    ax.barh(y, s_contrib, color=PALETTE["supply"], label="Supply Scarcity")
    ax.barh(y, t_contrib, left=s_contrib, color=PALETTE["access"], label="Travel Burden")
    ax.barh(y, p_contrib, left=s_contrib + t_contrib, color=PALETTE["peds"], label="Pediatric Gap")
    ax.barh(y, c_contrib, left=s_contrib + t_contrib + p_contrib,
            color=PALETTE["capacity"], label="Capacity Scarcity")

    ax.set_yticks(y)
    ax.set_yticklabels(top["label"], fontsize=10)
    ax.invert_yaxis()
    _style_ax(ax, "Highest-Burden Counties: BEI Component Breakdown",
              subtitle="Population-weighted average BEI across all tracts in each county",
              xlabel="BEI Score (0–100)")
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)

    for i, row in enumerate(top.itertuples()):
        rural_tag = f"{row.pct_rural:.0f}% rural"
        ax.text(row.bei + 0.5, i,
                f"BEI {row.bei:.0f} | Pop {row.pop:,.0f} | {rural_tag}",
                va="center", fontsize=8, color=PALETTE["muted"])

    fig.tight_layout()
    path = out_dir / "mn_08_hotspot_profile.png"
    _save(fig, path)
    return path


# ---------------------------------------------------------------------------
# USA figures (low detail)
# ---------------------------------------------------------------------------

def _recompute_usa_bei(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute USA county BEI using distance-based catchment metrics."""
    out = df.copy()
    out["t_score"] = robust_norm(out["t_sys"])
    fac = _load_facilities()

    _compute_supply_score_catchment(out, fac)
    _compute_peds_score_catchment(out, fac)
    _compute_capacity_score_catchment(out, fac)

    w = config.BEI_WEIGHTS
    out["bei"] = 100.0 * (
        w[0] * out["s_score"] + w[1] * out["t_score"] +
        w[2] * out["p_score"] + w[3] * out["c_score"]
    )
    out["bei_percentile"] = out["bei"].rank(pct=True) * 100
    return out


def fig_usa_01_county_bei_map(out_dir: Path) -> Path:
    """USA county-level BEI scatter map."""
    df = _load_usa_access()
    bei = _recompute_usa_bei(df)

    fig, ax = plt.subplots(figsize=(16, 10), facecolor="white")
    ax.set_facecolor("#F0F4F8")

    lower48 = bei[
        (bei["centroid_lat"] > 24) & (bei["centroid_lat"] < 50) &
        (bei["centroid_lon"] > -130) & (bei["centroid_lon"] < -65)
    ].copy()

    sc = ax.scatter(
        lower48["centroid_lon"], lower48["centroid_lat"],
        c=lower48["bei"], s=4, cmap=BEI_CMAP, vmin=0, vmax=100,
        edgecolors="none", alpha=0.8, zorder=2
    )
    cbar = plt.colorbar(sc, ax=ax, shrink=0.5, pad=0.02)
    cbar.set_label("Burn Equity Index (higher = more inequitable)", fontsize=10)

    fac = _load_facilities()
    lat_col = "latitude" if "latitude" in fac.columns else "centroid_lat"
    lon_col = "longitude" if "longitude" in fac.columns else "centroid_lon"
    valid_fac = fac[fac[lat_col].notna() & fac[lon_col].notna()]
    valid_fac = valid_fac[(valid_fac[lat_col] > 24) & (valid_fac[lat_col] < 50)]
    ax.scatter(valid_fac[lon_col], valid_fac[lat_col],
               marker="+", c=PALETTE["primary"], s=30, linewidth=0.8,
               zorder=5, alpha=0.8, label="Burn Centers")

    n_high = (lower48["bei"] >= lower48["bei"].quantile(0.9)).sum()
    pop_high = lower48.loc[lower48["bei"] >= lower48["bei"].quantile(0.9), "total_pop"].sum()
    ax.set_title(
        "National Burn Equity Index — County Level",
        fontsize=18, fontweight="bold", color=PALETTE["text"], pad=8, loc="left"
    )
    ax.text(0.0, 1.06,
            f"{n_high} high-burden counties (top 10%) affecting {pop_high:,.0f} residents",
            transform=ax.transAxes, fontsize=11, color=PALETTE["muted"], va="bottom")

    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)
    ax.set_axis_off()
    fig.tight_layout()
    path = out_dir / "usa_01_county_bei_map.png"
    _save(fig, path)

    bei.to_parquet(out_dir.parent / "tables" / "usa_bei_recomputed.parquet", index=False)
    return path


def fig_usa_02_state_rankings(out_dir: Path) -> Path:
    """State-level BEI ranking (population-weighted median)."""
    df = _load_usa_access()
    bei = _recompute_usa_bei(df)

    bei["state_fips"] = bei["county_fips"].astype(str).str.zfill(5).str[:2]
    from .bei_composite import FIPS_TO_ABBR

    state_bei = bei.groupby("state_fips", group_keys=False).apply(
        lambda g: pd.Series({
            "bei_median": g["bei"].median(),
            "bei_mean": (g["bei"] * g["total_pop"]).sum() / g["total_pop"].sum()
            if g["total_pop"].sum() > 0 else 0,
            "pop": g["total_pop"].sum(),
            "n_counties": len(g),
        }), include_groups=False
    ).reset_index()
    state_bei["state_abbr"] = state_bei["state_fips"].map(FIPS_TO_ABBR)
    state_bei = state_bei.dropna(subset=["state_abbr"])
    state_bei = state_bei.sort_values("bei_mean", ascending=False)

    top20 = state_bei.head(20)

    fig, ax = plt.subplots(figsize=(14, 8), facecolor="white")

    y = np.arange(len(top20))
    bars = ax.barh(y, top20["bei_mean"], color=PALETTE["accent"], alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(top20["state_abbr"], fontsize=10, fontweight="bold")
    ax.invert_yaxis()

    for i, (_, row) in enumerate(top20.iterrows()):
        ax.text(row["bei_mean"] + 0.5, i, f"BEI {row['bei_mean']:.1f} | Pop {row['pop']:,.0f}",
                va="center", fontsize=8, color=PALETTE["muted"])

    _style_ax(ax, "State Burn Equity Rankings",
              subtitle="Population-weighted average BEI (higher = more inequitable)",
              xlabel="BEI Score")

    fig.tight_layout()
    path = out_dir / "usa_02_state_rankings.png"
    _save(fig, path)
    return path


def fig_usa_03_coverage_gap(out_dir: Path) -> Path:
    """National coverage: % population by drive time + rural/urban overlay."""
    df = _load_usa_access()
    finite = df[np.isfinite(df["t_sys"])].copy()
    total_pop = finite["total_pop"].sum()

    thresholds = np.arange(0, 361, 10)
    pop_covered = []
    for t in thresholds:
        covered = finite.loc[finite["t_sys"] <= t, "total_pop"].sum()
        pop_covered.append(covered / total_pop * 100 if total_pop > 0 else 0)

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE, facecolor="white")
    ax.fill_between(thresholds, pop_covered, alpha=0.15, color=PALETTE["accent"])
    ax.plot(thresholds, pop_covered, color=PALETTE["accent"], linewidth=2.5)

    for t in [60, 120, 180, 240, 360]:
        idx = t // 10
        if idx < len(pop_covered):
            pct = pop_covered[idx]
            ax.plot(t, pct, "o", color=PALETTE["accent"], markersize=8, zorder=5)
            ax.annotate(f"{pct:.0f}% at {t} min",
                        xy=(t, pct), xytext=(t + 12, max(pct - 5, 5)),
                        fontsize=9, color=PALETTE["text"],
                        arrowprops=dict(arrowstyle="-", color=PALETTE["muted"], lw=0.8))

    _style_ax(ax, "National Population Coverage by Drive Time",
              subtitle=f"Total US population: {total_pop:,.0f}",
              xlabel="Maximum Drive Time to Nearest Burn Center (minutes)",
              ylabel="% Population Covered")
    ax.set_xlim(0, 360)
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())

    fig.tight_layout()
    path = out_dir / "usa_03_coverage_gap.png"
    _save(fig, path)
    return path


# ---------------------------------------------------------------------------
# Master runner
# ---------------------------------------------------------------------------

def generate_all(out_dir: Path | None = None) -> list[Path]:
    """Generate all presentation-ready figures and return the list of paths."""
    out = out_dir or config.FIGURES_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out.parent / "tables").mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    generators = [
        ("MN: Burn Center Map", fig_mn_01_burn_center_map),
        ("MN: Travel Time Map", fig_mn_02_travel_time_map),
        ("MN: Rural-Urban Gap", fig_mn_03_rural_urban_gap),
        ("MN: Coverage Curve", fig_mn_04_coverage_curve),
        ("MN: Access Pathways", fig_mn_05_access_pathway),
        ("MN: BEI Map", fig_mn_06_bei_map),
        ("MN: BEI Drivers", fig_mn_07_bei_drivers),
        ("MN: Hotspot Profile", fig_mn_08_hotspot_profile),
        ("USA: County BEI Map", fig_usa_01_county_bei_map),
        ("USA: State Rankings", fig_usa_02_state_rankings),
        ("USA: Coverage Gap", fig_usa_03_coverage_gap),
    ]

    for label, func in generators:
        try:
            LOG.info("Generating %s ...", label)
            p = func(out)
            if p:
                paths.append(p)
                LOG.info("  -> %s", p)
        except Exception:
            LOG.exception("Failed to generate %s", label)

    return paths


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    paths = generate_all()
    print(f"\nGenerated {len(paths)} presentation figures:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
