"""Choropleths, distribution plots, and comparison maps for dual-path outputs.

Generates MN tract-detail and USA county-detail visual outputs for judge-ready
presentation and frontend handoff.
"""
from __future__ import annotations

import logging
from pathlib import Path

from . import config
from .export import scoped_geojson_dir, scoped_tables_dir
from .presentation_scope import get_profile, list_profiles

LOG = logging.getLogger(__name__)

__all__ = [
    "config",
    "plot_mn_tract_bei_map",
    "plot_usa_county_bei_map",
    "run_visuals_for_profile",
    "run_all_visuals",
]


def _figures_dir(profile=None):
    """Return figures directory; ensure it exists."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return config.FIGURES_DIR


def _load_bei_geojson_or_table(profile):
    """Load BEI data as GeoDataFrame if GeoJSON exists, else DataFrame from parquet."""
    prefix = profile.output_prefix
    geojson_dir = scoped_geojson_dir(profile)
    tables_dir = scoped_tables_dir(profile)

    if profile.profile_id == "mn_high_detail":
        geojson_path = geojson_dir / f"{prefix}_tract_bei_ground.geojson"
        table_path = tables_dir / f"{prefix}_tract_bei.parquet"
        if not table_path.exists():
            table_path = tables_dir / "mn_mvp_tract_bei.parquet"
    else:
        geojson_path = geojson_dir / f"{prefix}_county_bei.geojson"
        table_path = tables_dir / f"{prefix}_county_bei.parquet"

    if geojson_path.exists():
        import geopandas as gpd
        return gpd.read_file(geojson_path), "geojson"
    if table_path.exists():
        import pandas as pd
        df = pd.read_parquet(table_path)
        if "centroid_lat" in df.columns and "centroid_lon" in df.columns:
            import geopandas as gpd
            from shapely.geometry import Point
            geom = [Point(float(r["centroid_lon"]), float(r["centroid_lat"])) for _, r in df.iterrows()]
            gdf = gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")
            return gdf, "points"
        return df, "table"
    return None, None


def plot_mn_tract_bei_map(profile=None, out_path: Path | None = None) -> Path | None:
    """Create MN tract-level BEI map figure (point or choropleth).

    Saves to FIGURES_DIR with profile output_prefix, e.g. mn_high_detail_tract_bei_map.png.
    """
    import matplotlib.pyplot as plt

    profile = profile or get_profile("mn_high_detail")
    data, kind = _load_bei_geojson_or_table(profile)
    if data is None:
        LOG.warning("No MN tract BEI data found; skipping tract BEI map.")
        return None

    fig_dir = _figures_dir(profile)
    path = out_path or (fig_dir / f"{profile.output_prefix}_tract_bei_map.png")

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    if hasattr(data, "geometry"):
        if "bei" in data.columns:
            data.plot(ax=ax, column="bei", legend=True, cmap="YlOrRd", legend_kwds={"label": "BEI"})
        else:
            data.plot(ax=ax, color="steelblue", alpha=0.6)
    else:
        if "centroid_lon" in data.columns and "centroid_lat" in data.columns and "bei" in data.columns:
            sc = ax.scatter(data["centroid_lon"], data["centroid_lat"], c=data["bei"], s=2, cmap="YlOrRd")
            plt.colorbar(sc, ax=ax, label="BEI")
    ax.set_title(f"{profile.display_name} — Tract BEI")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    LOG.info("Wrote %s", path)
    return path


def plot_usa_county_bei_map(profile=None, out_path: Path | None = None) -> Path | None:
    """Create USA county-level BEI map figure.

    Saves to FIGURES_DIR, e.g. usa_low_detail_county_county_bei_map.png.
    """
    import matplotlib.pyplot as plt

    profile = profile or get_profile("usa_low_detail_county")
    data, kind = _load_bei_geojson_or_table(profile)
    if data is None:
        LOG.warning("No USA county BEI data found; skipping county BEI map.")
        return None

    fig_dir = _figures_dir(profile)
    path = out_path or (fig_dir / f"{profile.output_prefix}_county_bei_map.png")

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    if hasattr(data, "geometry"):
        if "bei" in data.columns:
            data.plot(ax=ax, column="bei", legend=True, cmap="YlOrRd", legend_kwds={"label": "BEI"})
        else:
            data.plot(ax=ax, color="steelblue", alpha=0.5)
    else:
        if "centroid_lon" in data.columns and "centroid_lat" in data.columns and "bei" in data.columns:
            sc = ax.scatter(data["centroid_lon"], data["centroid_lat"], c=data["bei"], s=1, cmap="YlOrRd")
            plt.colorbar(sc, ax=ax, label="BEI")
    ax.set_title(f"{profile.display_name} — County BEI")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    LOG.info("Wrote %s", path)
    return path


def run_visuals_for_profile(profile) -> list[Path]:
    """Generate all visual outputs for one dataset profile."""
    paths = []
    if profile.profile_id == "mn_high_detail":
        p = plot_mn_tract_bei_map(profile)
        if p:
            paths.append(p)
    elif profile.profile_id == "usa_low_detail_county":
        p = plot_usa_county_bei_map(profile)
        if p:
            paths.append(p)
    return paths


def run_all_visuals() -> list[Path]:
    """Generate MN tract-detail and USA county-detail visual outputs for all profiles."""
    all_paths = []
    for profile in list_profiles():
        all_paths.extend(run_visuals_for_profile(profile))
    return all_paths


def main() -> None:
    """Generate dual-path visual outputs (MN tract + USA county)."""
    logging.basicConfig(level=logging.INFO)
    paths = run_all_visuals()
    print(f"Visualize complete: {len(paths)} figure(s) written to {config.FIGURES_DIR}.")


if __name__ == "__main__":
    main()
