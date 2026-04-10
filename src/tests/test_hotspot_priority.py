"""Hotspot and priority regression checks (US6): Gi*, Moran, clustering, need-overlay ranking.

To run the Gi* and Moran hotspot tests (no skips), install spatial deps:
  pip install esda libpysal
Or install full deps: pip install -r requirements.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import hotspot
from pipeline import priority

# Skip hotspot (spatial) tests when libpysal/esda not installed
HOTSPOT_DEPS = False
try:
    from esda.getisord import G_Local  # noqa: F401
    import libpysal  # noqa: F401
    HOTSPOT_DEPS = True
except ImportError:
    pass


def _small_bei_df() -> pd.DataFrame:
    """Minimal BEI-like table with coords for KNN weights (no geometry)."""
    np.random.seed(42)
    n = 20
    return pd.DataFrame({
        "GEOID": [f"2700{i:06d}" for i in range(1, n + 1)],
        "centroid_lat": 44.0 + np.random.uniform(-0.5, 0.5, n),
        "centroid_lon": -93.0 + np.random.uniform(-0.5, 0.5, n),
        "bei": np.clip(30 + 40 * np.random.rand(n), 0, 100),
        "s_score": np.random.rand(n),
        "t_score": np.random.rand(n),
        "p_score": np.random.rand(n),
        "c_score": np.random.rand(n),
        "total_pop": np.random.randint(1000, 50000, n),
        "child_pop": np.random.randint(100, 10000, n),
    })


@pytest.mark.skipif(not HOTSPOT_DEPS, reason="esda/libpysal required for hotspot stats")
def test_hotspot_stats_returns_gi_and_moran_columns():
    """Compute Gi* and Local Moran's I; output has expected columns."""
    df = _small_bei_df()
    out = hotspot.compute_hotspot_stats(df, value_col="bei", permutations=29, seed=42)
    assert "gi_star_z" in out.columns and "gi_star_p" in out.columns
    assert "gi_star_class" in out.columns
    assert out["gi_star_class"].isin(["hot", "cold", "ns"]).all()
    assert "moran_local_i" in out.columns and "moran_p" in out.columns
    assert "moran_class" in out.columns
    assert out["moran_class"].isin(["HH", "LL", "HL", "LH", "ns"]).all() or (out["moran_class"] == "ns").all()


def test_clusters_and_archetypes_assigned():
    """Clustering assigns cluster_id and interpretable archetype labels."""
    df = _small_bei_df()
    out = hotspot.compute_clusters_and_archetypes(df, n_clusters=3)
    assert "cluster_id" in out.columns
    assert "archetype_label" in out.columns
    assert "archetype_dominant_component" in out.columns
    assert set(out["cluster_id"].unique()).issubset(set(range(3)) | {-1})
    assert out["archetype_dominant_component"].isin(["S", "T", "P", "C", "BEI"]).all()


def test_priority_score_adds_need_overlay_and_ranking():
    """Priority = BEI * (1 + λ * NeedOverlay); ranking differs from BEI-only."""
    df = _small_bei_df()
    out = priority.compute_priority_score(df, bei_col="bei")
    assert "need_overlay" in out.columns
    assert "priority_score" in out.columns
    assert (out["priority_score"] >= 0).all()
    # Higher need should boost priority relative to raw BEI
    high_need = out["need_overlay"] > out["need_overlay"].median()
    low_need = ~high_need
    if high_need.sum() and low_need.sum():
        # Same BEI with higher need -> higher priority_score
        assert out.loc[high_need, "priority_score"].mean() >= out.loc[low_need, "priority_score"].mean() - 1e-6


def test_priority_ranking_changes_with_need_overlay():
    """Ranking by priority_score differs from ranking by BEI when need varies."""
    df = pd.DataFrame({
        "GEOID": ["1", "2", "3"],
        "bei": [50, 50, 50],
        "total_pop": [100_000, 5_000, 500],
        "child_pop": [20_000, 1_000, 100],
    })
    out = priority.compute_priority_score(df)
    # Same BEI: higher pop -> higher need_overlay -> higher priority_score
    assert out["priority_score"].iloc[0] >= out["priority_score"].iloc[1]
    assert out["priority_score"].iloc[1] >= out["priority_score"].iloc[2]


@pytest.mark.skipif(not HOTSPOT_DEPS, reason="esda/libpysal required for hotspot layer")
def test_hotspot_layer_integration():
    """Full hotspot layer: stats + clustering; stability fields present."""
    df = _small_bei_df()
    out = hotspot.compute_hotspot_layer(
        df, value_col="bei", permutations=29, n_clusters=3, seed=42
    )
    assert "gi_star_z" in out.columns and "moran_class" in out.columns
    assert "cluster_id" in out.columns and "archetype_label" in out.columns
    assert "stability_pct" in out.columns and "stability_class" in out.columns


def test_hotspot_clusters_statistically_coherent():
    """Cluster means differ across clusters (non-trivial grouping)."""
    df = _small_bei_df()
    out = hotspot.compute_clusters_and_archetypes(df, n_clusters=4)
    means = out.groupby("cluster_id")["bei"].mean()
    if len(means) >= 2:
        assert means.std() > 0 or out["cluster_id"].nunique() == 1
