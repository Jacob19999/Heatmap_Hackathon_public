"""
Spatial hotspot detection (Gi*, Local Moran's I), clustering (K-means, HDBSCAN),
and archetype labeling from tract or county BEI outputs.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import config

LOG = logging.getLogger(__name__)

# Optional heavy deps (spatial + clustering)
try:
    import libpysal
    from esda.getisord import G_Local
    from esda.moran import Moran_Local
except ImportError as e:
    libpysal = None  # type: ignore[assignment]
    G_Local = None  # type: ignore[assignment]
    Moran_Local = None  # type: ignore[assignment]
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ImportError as e:
    KMeans = None  # type: ignore[assignment]
    StandardScaler = None  # type: ignore[assignment]
    _SKLEARN_ERROR = e
else:
    _SKLEARN_ERROR = None

try:
    import hdbscan
except ImportError:
    hdbscan = None  # type: ignore[assignment]

__all__ = [
    "config",
    "compute_hotspot_stats",
    "compute_clusters_and_archetypes",
    "compute_hotspot_layer",
]


def _spatial_weights(
    df: pd.DataFrame,
    geometry_col: str = "geometry",
    id_col: str | None = None,
    lat_col: str = "centroid_lat",
    lon_col: str = "centroid_lon",
):
    """Build libpysal spatial weights from geometry or from lat/lon (KNN).

    Returns W. Weights are aligned to id_col values (GEOID or county_fips).
    """
    if libpysal is None or _IMPORT_ERROR is not None:
        raise RuntimeError("libpysal and esda are required for hotspot statistics") from _IMPORT_ERROR

    id_col = id_col or _id_column(df)
    ids = df[id_col].astype(str).tolist()

    if geometry_col in df.columns and hasattr(df, "geometry"):
        try:
            import geopandas as gpd
            if not isinstance(df, gpd.GeoDataFrame):
                gdf = gpd.GeoDataFrame(df, geometry=df[geometry_col], crs="EPSG:4326")
            else:
                gdf = df.copy()
            gdf = gdf.set_index(id_col)
            w = libpysal.weights.Queen.from_dataframe(gdf)
            return w
        except Exception as e:
            LOG.warning("Queen weights from geometry failed: %s; falling back to KNN", e)

    if lat_col in df.columns and lon_col in df.columns:
        coords = df[[lon_col, lat_col]].astype(float).values
        coords = np.nan_to_num(coords, nan=0.0)
        w = libpysal.weights.KNN.from_array(coords, k=min(8, len(coords) - 1) if len(coords) > 1 else 1)
        # KNN id_order is 0..n-1; we'll align by position when building y
        return w

    raise ValueError("Need either geometry column or centroid_lat/centroid_lon for spatial weights.")


def _id_column(df: pd.DataFrame) -> str:
    if "GEOID" in df.columns:
        return "GEOID"
    if "county_fips" in df.columns:
        return "county_fips"
    raise ValueError("DataFrame must have GEOID or county_fips as geography id.")


def compute_hotspot_stats(
    df: pd.DataFrame,
    value_col: str = "bei",
    alpha: float = 0.05,
    permutations: int = 999,
    seed: int | None = None,
) -> pd.DataFrame:
    """Compute Getis-Ord Gi* and Local Moran's I for BEI (or any value column).

    Expects df to have geometry or centroid_lat/centroid_lon for spatial weights.
    Adds: gi_star_z, gi_star_p, gi_star_class, moran_local_i, moran_p, moran_class.
    """
    if G_Local is None or Moran_Local is None:
        raise RuntimeError("esda is required for hotspot statistics") from _IMPORT_ERROR

    id_col = _id_column(df)
    w = _spatial_weights(df, id_col=id_col)

    # Align y with w.id_order. Queen uses geo ids; KNN uses 0..n-1.
    id_order = list(w.id_order) if hasattr(w, "id_order") else list(range(len(df)))
    try:
        is_positional = all(isinstance(i, (int, np.integer)) and 0 <= i < len(df) for i in id_order)
    except (TypeError, ValueError):
        is_positional = False
    if is_positional and len(id_order) == len(df):
        y = df[value_col].astype(float).fillna(0).values
        result_idx = id_order
    else:
        # Weights indexed by geography id
        y = df.set_index(id_col).astype(str).reindex(id_order)[value_col].fillna(0).values
        result_idx = id_order

    n = len(df)
    gi = G_Local(y, w, transform="B", star=True, permutations=permutations, seed=seed)
    moran = Moran_Local(y, w, permutations=permutations, seed=seed)

    # Map results back to df rows by id
    gi_series = pd.Series(np.asarray(gi.Zs), index=result_idx)
    gi_p_series = pd.Series(np.asarray(gi.p_sim), index=result_idx)
    moran_i_series = pd.Series(np.asarray(moran.Is), index=result_idx)
    moran_p_series = pd.Series(np.asarray(moran.p_sim), index=result_idx)
    moran_q_series = pd.Series(np.asarray(moran.q), index=result_idx)

    if is_positional:
        out = df.copy()
        out["gi_star_z"] = gi_series.values
        out["gi_star_p"] = gi_p_series.values
        out["moran_local_i"] = moran_i_series.values
        out["moran_p"] = moran_p_series.values
        moran_q_vals = moran_q_series.values
    else:
        out = df.copy()
        out["gi_star_z"] = out[id_col].astype(str).map(gi_series)
        out["gi_star_p"] = out[id_col].astype(str).map(gi_p_series)
        out["moran_local_i"] = out[id_col].astype(str).map(moran_i_series)
        out["moran_p"] = out[id_col].astype(str).map(moran_p_series)
        moran_q_vals = out[id_col].astype(str).map(moran_q_series).values

    out["gi_star_class"] = np.where(out["gi_star_p"].fillna(1) >= alpha, "ns", np.where(out["gi_star_z"] > 0, "hot", "cold"))
    quad_map = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    out["moran_class"] = np.where(out["moran_p"].fillna(1) >= alpha, "ns", [quad_map.get(int(q), "ns") if pd.notna(q) and not np.isnan(q) else "ns" for q in moran_q_vals])
    return out


def _cluster_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Build z-scored feature matrix for clustering. Returns (matrix, feature_names)."""
    comps = ["s_score", "t_score", "p_score", "c_score"]
    optional = ["nearest_burn_time", "t_sys", "centers_per_100k", "beds_per_100k", "peds_access", "ruca_code"]
    cols = [c for c in comps if c in df.columns]
    for c in optional:
        if c in df.columns and c not in cols:
            cols.append(c)
    if "bei" in df.columns and "bei" not in cols:
        cols.insert(0, "bei")
    if not cols:
        cols = [c for c in df.columns if df[c].dtype in (np.floating, np.int64, np.int32) and c != "geometry"][:10]
    X = df[cols].astype(float).fillna(0).values
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    return X, cols


def _dominant_component(profile: dict[str, float]) -> str:
    """Which of S,T,P,C has the lowest (worst) score; that drives the archetype."""
    comps = ["S", "T", "P", "C"]
    keys = [f"{c.lower()}_score" for c in comps]
    means = [profile.get(k, 0.5) for k in keys]
    if not means:
        return "BEI"
    idx = int(np.argmin(means))
    return comps[idx]


def compute_clusters_and_archetypes(
    df: pd.DataFrame,
    n_clusters: int = 6,
    use_hdbscan: bool = False,
    min_cluster_size: int = 5,
) -> pd.DataFrame:
    """Assign cluster_id and archetype_label from K-means (and optionally HDBSCAN).

    Uses standardized S, T, P, C and companion metrics. Archetype = dominant component
    (lowest mean score) per cluster. Noise from HDBSCAN gets cluster_id = -1.
    """
    if KMeans is None or StandardScaler is None:
        raise RuntimeError("sklearn is required for clustering") from _SKLEARN_ERROR

    X, feat_names = _cluster_feature_matrix(df)
    n = len(X)
    if n < n_clusters:
        out = df.copy()
        out["cluster_id"] = 0
        out["archetype_label"] = "single_geography"
        out["archetype_dominant_component"] = "BEI"
        return out

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels_k = kmeans.fit_predict(X)
    out = df.copy()
    out["cluster_id"] = labels_k

    if use_hdbscan and hdbscan is not None and n >= min_cluster_size * 2:
        try:
            clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=1)
            labels_h = clusterer.fit_predict(X)
            # Prefer HDBSCAN when it finds multiple clusters; else keep K-means
            n_h = len(set(labels_h)) - (1 if -1 in labels_h else 0)
            if n_h >= 2:
                out["cluster_id"] = labels_h
        except Exception as e:
            LOG.warning("HDBSCAN failed, using K-means only: %s", e)

    # Archetype per cluster: mean profile then dominant component
    comp_cols = [c for c in ["s_score", "t_score", "p_score", "c_score"] if c in out.columns]
    if not comp_cols:
        out["archetype_label"] = "cluster_" + out["cluster_id"].astype(str)
        out["archetype_dominant_component"] = "BEI"
        return out

    out["archetype_label"] = ""
    out["archetype_dominant_component"] = "BEI"
    for cid in sorted(out["cluster_id"].unique()):
        mask = out["cluster_id"] == cid
        if cid == -1:
            out.loc[mask, "archetype_label"] = "noise"
            out.loc[mask, "archetype_dominant_component"] = "BEI"
            continue
        sub = out.loc[mask, comp_cols]
        profile = sub.mean().to_dict()
        dom = _dominant_component(profile)
        out.loc[mask, "archetype_label"] = f"{dom}_driven"
        out.loc[mask, "archetype_dominant_component"] = dom
    return out


def compute_hotspot_layer(
    bei_df: pd.DataFrame,
    value_col: str = "bei",
    alpha: float = 0.05,
    permutations: int = 99,
    n_clusters: int = 6,
    use_hdbscan: bool = False,
    seed: int | None = 42,
) -> pd.DataFrame:
    """Full hotspot pipeline: Gi* + Moran Local + clustering + archetypes.

    BEI table must have geometry or centroid_lat/centroid_lon for spatial stats.
    Optionally add priority_score/need_overlay by merging with priority.compute_priority_score.
    stability_pct / stability_class left as NaN (filled when sensitivity runs exist).
    """
    if "geometry" not in bei_df.columns and "centroid_lat" not in bei_df.columns:
        raise ValueError("BEI table must have geometry or centroid_lat/centroid_lon for hotspot layer.")

    out = compute_hotspot_stats(bei_df, value_col=value_col, alpha=alpha, permutations=permutations, seed=seed)
    out = compute_clusters_and_archetypes(out, n_clusters=n_clusters, use_hdbscan=use_hdbscan)
    out["stability_pct"] = np.nan
    out["stability_class"] = ""
    return out
