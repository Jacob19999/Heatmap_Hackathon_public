"""Export tract/county/state tables and GeoJSON to Data/output.

This module owns scope-aware conventions for presentation profiles (MN high-detail,
USA low-detail county) and generates profile-aware table/GeoJSON payloads for
frontend consumption.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

import json
import pandas as pd

from . import config
from .presentation_scope import DatasetProfile, get_profile, list_profiles

LOG = logging.getLogger(__name__)

__all__ = [
    "config",
    "DatasetProfile",
    "get_profile",
    "scoped_tables_dir",
    "scoped_geojson_dir",
    "manifest_path_for_profile",
    "write_presentation_manifest",
    "write_product_views_manifest",
    "write_default_dual_path_product_views_manifest",
    "export_profile_geojson",
    "get_profile_assets",
]


def scoped_tables_dir(profile: DatasetProfile | None = None) -> Path:
    """Return the tables directory for a given profile (currently shared)."""
    _ = profile or get_profile()
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    return config.TABLES_DIR


def scoped_geojson_dir(profile: DatasetProfile | None = None) -> Path:
    """Return the geojson directory for a given profile (currently shared)."""
    _ = profile or get_profile()
    config.GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
    return config.GEOJSON_DIR


def manifest_path_for_profile(profile: DatasetProfile | None = None) -> Path:
    """Return the manifest path for a given profile."""
    prof = profile or get_profile()
    config.MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    return config.MANIFESTS_DIR / f"{prof.output_prefix}_manifest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_presentation_manifest(
    profile: DatasetProfile,
    assets: Mapping[str, Mapping[str, Mapping[str, str]]],
    methodology: Mapping[str, Any],
    ui_defaults: Mapping[str, Any],
    facility_assets: Mapping[str, str] | None = None,
    manifest_version: str = "1.0.0",
) -> Path:
    """Write a presentation manifest JSON file for the given profile.

    The shape is aligned with `contracts/presentation_manifest.schema.json`.
    """
    path = manifest_path_for_profile(profile)
    payload: Dict[str, Any] = {
        "manifest_version": manifest_version,
        "generated_at": _now_iso(),
        "profile": {
            "id": profile.profile_id,
            "display_name": profile.display_name,
            "scope_level": profile.scope_level,
            "output_prefix": profile.output_prefix,
            "origin_state_fips": list(profile.origin_state_fips),
            "destination_region": list(profile.destination_state_filter),
            "notes": profile.notes,
        },
        "scenarios": {
            "default": profile.default_scenario,
            "enabled": list(profile.enabled_scenarios),
        },
        "assets": {k: dict(v) for k, v in assets.items()},
        "facility_assets": dict(facility_assets or {}),
        "methodology": dict(methodology),
        "ui_defaults": dict(ui_defaults),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_product_views_manifest(
    views: Mapping[str, Mapping[str, Any]],
    product_name: str = "Burn Care Equity Intelligence Platform",
    manifest_version: str = "1.0.0",
) -> Path:
    """Write the top-level product views manifest for frontend tabs.

    `views` is a mapping from view_id to a dict with keys:
      - label
      - detail_level
      - dataset_profile_id
      - manifest_path
      - default_metric
      - default_geography_level
      - badge_text (optional)
      - description (optional)
    """
    config.MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.MANIFESTS_DIR / "product_views_manifest.json"
    payload: Dict[str, Any] = {
        "manifest_version": manifest_version,
        "generated_at": _now_iso(),
        "product_name": product_name,
        "views": [],
    }
    for view_id, spec in views.items():
        entry = {"view_id": view_id}
        entry.update(spec)
        payload["views"].append(entry)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_default_dual_path_product_views_manifest() -> Path:
    """Convenience helper to publish the MN/USA dual-path product views.

    This wires up:
      - `mn_high_detail_tab` -> `mn_high_detail` profile (tract-level MN)
      - `usa_low_detail_county_tab` -> `usa_low_detail_county` profile (county-level USA)
    """
    mn = get_profile("mn_high_detail")
    usa = get_profile("usa_low_detail_county")

    mn_manifest_rel = manifest_path_for_profile(mn).relative_to(config.OUTPUT_DIR)
    usa_manifest_rel = manifest_path_for_profile(usa).relative_to(config.OUTPUT_DIR)

    views: Dict[str, Any] = {
        "mn_high_detail_tab": {
            "label": "Minnesota – High Detail",
            "detail_level": "high",
            "dataset_profile_id": mn.profile_id,
            "manifest_path": str(mn_manifest_rel),
            "default_metric": "bei",
            "default_geography_level": "tract",
            "badge_text": "High Detail",
            "description": "Tract-level Burn Equity Index and access patterns for Minnesota.",
        },
        "usa_low_detail_county_tab": {
            "label": "USA – Low Detail (County)",
            "detail_level": "low",
            "dataset_profile_id": usa.profile_id,
            "manifest_path": str(usa_manifest_rel),
            "default_metric": "bei",
            "default_geography_level": "county",
            "badge_text": "Low Detail",
            "description": "County-level Burn Equity Index for a fast national overview.",
        },
    }

    return write_product_views_manifest(views=views)


def _write_geojson_from_centroids(
    df: pd.DataFrame,
    id_col: str,
    lat_col: str,
    lon_col: str,
    out_path: Path,
    props: list[str] | None = None,
) -> None:
    """Write a GeoJSON file from a DataFrame with centroid lat/lon (point geometry)."""
    import geopandas as gpd
    from shapely.geometry import Point

    out_path.parent.mkdir(parents=True, exist_ok=True)
    for c in (id_col, lat_col, lon_col):
        if c not in df.columns:
            raise ValueError(f"DataFrame missing required column: {c}")
    use = df[[id_col, lat_col, lon_col]].dropna(subset=[lat_col, lon_col]).copy()
    if props:
        for p in props:
            if p in df.columns:
                use[p] = df.loc[use.index, p]
    geometry = [Point(float(r[lon_col]), float(r[lat_col])) for _, r in use.iterrows()]
    gdf = gpd.GeoDataFrame(use, geometry=geometry, crs="EPSG:4326")
    gdf.to_file(out_path, driver="GeoJSON", index=False)


def export_profile_geojson(profile: DatasetProfile) -> Dict[str, Path]:
    """Generate profile-aware GeoJSON payloads for the given profile.

    Writes GeoJSON to scoped_geojson_dir using the profile output_prefix.
    Returns a dict of written paths keyed by asset name (e.g. 'tract_bei_geojson',
    'county_bei_geojson'). Skips writing if required source tables are missing.
    """
    written: Dict[str, Path] = {}
    prefix = profile.output_prefix
    tables_dir = scoped_tables_dir(profile)
    geojson_dir = scoped_geojson_dir(profile)
    geojson_dir.mkdir(parents=True, exist_ok=True)

    if profile.profile_id == "mn_high_detail":
        bei_path = tables_dir / f"{prefix}_tract_bei.parquet"
        if not bei_path.exists():
            LOG.debug("Skipping tract BEI GeoJSON: %s not found", bei_path)
            return written
        bei_df = pd.read_parquet(bei_path)
        id_col = "GEOID" if "GEOID" in bei_df.columns else "tract_geoid"
        if id_col not in bei_df.columns:
            LOG.warning("Tract BEI table missing %s; skipping GeoJSON", id_col)
            return written
        if "centroid_lat" in bei_df.columns and "centroid_lon" in bei_df.columns:
            out_path = geojson_dir / f"{prefix}_tract_bei_ground.geojson"
            props = [c for c in ("bei", "s_score", "t_score", "p_score", "c_score", "total_pop",
                "svi_overall", "svi_theme1", "svi_theme2", "svi_theme3", "svi_theme4") if c in bei_df.columns]
            _write_geojson_from_centroids(bei_df, id_col, "centroid_lat", "centroid_lon", out_path, props=props)
            written["tract_bei_geojson"] = out_path
            LOG.info("Wrote tract BEI GeoJSON: %s", out_path)
        else:
            try:
                from .routing_inputs import build_tract_origins
                tracts = build_tract_origins()
                merge_col = "GEOID" if "GEOID" in tracts.columns else "tract_geoid"
                if merge_col not in tracts.columns or id_col not in bei_df.columns:
                    LOG.warning("Cannot join tract BEI to centroids; skipping GeoJSON")
                    return written
                merged = bei_df.merge(
                    tracts[[merge_col, "centroid_lat", "centroid_lon"]].drop_duplicates(merge_col),
                    left_on=id_col,
                    right_on=merge_col,
                    how="inner",
                )
                if merged.empty:
                    LOG.warning("Tract BEI merge with origins produced no rows; skipping GeoJSON")
                    return written
                out_path = geojson_dir / f"{prefix}_tract_bei_ground.geojson"
                props = [c for c in ("bei", "s_score", "t_score", "p_score", "c_score", "total_pop",
                    "svi_overall", "svi_theme1", "svi_theme2", "svi_theme3", "svi_theme4") if c in merged.columns]
                _write_geojson_from_centroids(merged, id_col, "centroid_lat", "centroid_lon", out_path, props=props)
                written["tract_bei_geojson"] = out_path
                LOG.info("Wrote tract BEI GeoJSON: %s", out_path)
            except Exception as e:
                LOG.warning("Could not build tract BEI GeoJSON: %s", e)
        # Air-sensitivity: tract-level delta GeoJSON when parquet exists
        tract_delta_path = tables_dir / f"{prefix}_tract_air_delta.parquet"
        if tract_delta_path.exists():
            try:
                delta_df = pd.read_parquet(tract_delta_path)
                id_col = "tract_geoid"
                if id_col not in delta_df.columns:
                    LOG.debug("Skipping tract air-delta GeoJSON: missing %s", id_col)
                else:
                    from .routing_inputs import build_tract_origins
                    tracts = build_tract_origins()
                    merge_col = "GEOID" if "GEOID" in tracts.columns else "tract_geoid"
                    if merge_col in tracts.columns:
                        merged = delta_df.merge(
                            tracts[[merge_col, "centroid_lat", "centroid_lon"]].drop_duplicates(merge_col),
                            left_on=id_col,
                            right_on=merge_col,
                            how="inner",
                        )
                        if not merged.empty:
                            props = [c for c in ("bei_ground", "bei_air", "bei_delta", "t_sys_ground", "t_sys_air", "t_delta", "air_feasible", "air_materially_helps") if c in merged.columns]
                            out_path = geojson_dir / f"{prefix}_tract_air_delta.geojson"
                            _write_geojson_from_centroids(merged, id_col, "centroid_lat", "centroid_lon", out_path, props=props)
                            written["tract_air_delta_geojson"] = out_path
                            LOG.info("Wrote tract air-delta GeoJSON: %s", out_path)
            except Exception as e:
                LOG.warning("Could not build tract air-delta GeoJSON: %s", e)

    elif profile.profile_id == "usa_low_detail_county":
        bei_path = tables_dir / f"{prefix}_county_bei.parquet"
        if not bei_path.exists():
            LOG.debug("Skipping county BEI GeoJSON: %s not found", bei_path)
            return written
        county_bei = pd.read_parquet(bei_path)
        if "county_fips" not in county_bei.columns:
            LOG.warning("County BEI table missing county_fips; skipping GeoJSON")
            return written
        # Use county_bei directly if it has centroids; otherwise merge with origins
        if "centroid_lat" in county_bei.columns and "centroid_lon" in county_bei.columns:
            use_df = county_bei
        else:
            origins_path = config.TABLES_DIR / "usa_low_detail_county_county_origins.parquet"
            if not origins_path.exists():
                LOG.warning("County origins not found at %s; skipping county BEI GeoJSON", origins_path)
                return written
            origins = pd.read_parquet(origins_path)
            merged = county_bei.merge(
                origins[["county_fips", "centroid_lat", "centroid_lon"]].drop_duplicates("county_fips"),
                on="county_fips",
                how="inner",
            )
            if merged.empty:
                LOG.warning("County BEI merge with origins produced no rows; skipping GeoJSON")
                return written
            use_df = merged
        out_path = geojson_dir / f"{prefix}_county_bei.geojson"
        props = [c for c in ("bei", "s_score", "t_score", "p_score", "c_score", "total_pop",
            "svi_overall", "svi_theme1", "svi_theme2", "svi_theme3", "svi_theme4") if c in use_df.columns]
        _write_geojson_from_centroids(use_df, "county_fips", "centroid_lat", "centroid_lon", out_path, props=props)
        written["county_bei_geojson"] = out_path
        LOG.info("Wrote county BEI GeoJSON: %s", out_path)
        # Air-sensitivity: county-level delta GeoJSON when parquet exists
        county_delta_path = tables_dir / f"{prefix}_county_air_delta.parquet"
        if county_delta_path.exists():
            try:
                delta_df = pd.read_parquet(county_delta_path)
                if "county_fips" not in delta_df.columns:
                    LOG.debug("Skipping county air-delta GeoJSON: missing county_fips")
                else:
                    if "centroid_lat" in delta_df.columns and "centroid_lon" in delta_df.columns:
                        use_delta = delta_df
                    else:
                        origins_path = config.TABLES_DIR / "usa_low_detail_county_county_origins.parquet"
                        if origins_path.exists():
                            origins = pd.read_parquet(origins_path)
                            use_delta = delta_df.merge(
                                origins[["county_fips", "centroid_lat", "centroid_lon"]].drop_duplicates("county_fips"),
                                on="county_fips",
                                how="inner",
                            )
                        else:
                            use_delta = pd.DataFrame()
                    if not use_delta.empty:
                        props = [c for c in ("bei_ground", "bei_air", "bei_delta", "t_sys_ground", "t_sys_air", "t_delta", "air_feasible", "air_materially_helps") if c in use_delta.columns]
                        out_path = geojson_dir / f"{prefix}_county_air_delta.geojson"
                        _write_geojson_from_centroids(use_delta, "county_fips", "centroid_lat", "centroid_lon", out_path, props=props)
                        written["county_air_delta_geojson"] = out_path
                        LOG.info("Wrote county air-delta GeoJSON: %s", out_path)
            except Exception as e:
                LOG.warning("Could not build county air-delta GeoJSON: %s", e)

    return written


def get_profile_assets(profile: DatasetProfile) -> Dict[str, Dict[str, Dict[str, str]]]:
    """Build the assets map for write_presentation_manifest for the given profile.

    Ensures profile-aware GeoJSON are written (via export_profile_geojson), then
    returns assets keyed by geography level and scenario with table/geojson paths
    relative to OUTPUT_DIR.
    """
    tables_dir = scoped_tables_dir(profile)
    geojson_paths = export_profile_geojson(profile)

    if profile.profile_id == "mn_high_detail":
        prefix = profile.output_prefix
        tract_bei = tables_dir / f"{prefix}_tract_bei.parquet"
        tract_access = tables_dir / f"{prefix}_tract_access.parquet"
        if not tract_bei.exists():
            tract_bei = tables_dir / "mn_mvp_tract_bei.parquet"
        if not tract_access.exists():
            tract_access = tables_dir / "mn_mvp_tract_access.parquet"
        assets = {
            "tract": {
                "ground_only": {
                    "table": str(tract_bei.resolve().relative_to(config.OUTPUT_DIR)),
                    "access_table": str(tract_access.resolve().relative_to(config.OUTPUT_DIR)),
                }
            }
        }
        if "tract_bei_geojson" in geojson_paths:
            assets["tract"]["ground_only"]["geojson"] = str(
                geojson_paths["tract_bei_geojson"].resolve().relative_to(config.OUTPUT_DIR)
            )
        # Air-sensitivity scenario: delta table and optional GeoJSON when present
        tract_delta_table = tables_dir / f"{prefix}_tract_air_delta.parquet"
        if tract_delta_table.exists():
            assets["tract"]["ground_plus_air"] = {
                "delta_table": str(tract_delta_table.resolve().relative_to(config.OUTPUT_DIR)),
            }
            if "tract_air_delta_geojson" in geojson_paths:
                assets["tract"]["ground_plus_air"]["delta_geojson"] = str(
                    geojson_paths["tract_air_delta_geojson"].resolve().relative_to(config.OUTPUT_DIR)
                )

    elif profile.profile_id == "usa_low_detail_county":
        prefix = profile.output_prefix
        county_bei = tables_dir / f"{prefix}_county_bei.parquet"
        county_access = tables_dir / f"{prefix}_county_access.parquet"
        assets = {
            "county": {
                "ground_only": {
                    "table": str(county_bei.resolve().relative_to(config.OUTPUT_DIR)),
                    "access_table": str(county_access.resolve().relative_to(config.OUTPUT_DIR)),
                }
            }
        }
        if "county_bei_geojson" in geojson_paths:
            assets["county"]["ground_only"]["geojson"] = str(
                geojson_paths["county_bei_geojson"].resolve().relative_to(config.OUTPUT_DIR)
            )
        # Air-sensitivity scenario: county-level delta table and optional GeoJSON when present
        county_delta_table = tables_dir / f"{prefix}_county_air_delta.parquet"
        if county_delta_table.exists():
            assets["county"]["ground_plus_air"] = {
                "delta_table": str(county_delta_table.resolve().relative_to(config.OUTPUT_DIR)),
            }
            if "county_air_delta_geojson" in geojson_paths:
                assets["county"]["ground_plus_air"]["delta_geojson"] = str(
                    geojson_paths["county_air_delta_geojson"].resolve().relative_to(config.OUTPUT_DIR)
                )

    else:
        assets = {}

    return assets


def main() -> None:
    """Emit profile manifests and the default dual-tab product views manifest."""
    import logging
    logging.basicConfig(level=logging.INFO)
    for profile in list_profiles():
        export_profile_geojson(profile)
    write_default_dual_path_product_views_manifest()
    print("Export complete: GeoJSON and product_views_manifest.json written.")


if __name__ == "__main__":
    main()

