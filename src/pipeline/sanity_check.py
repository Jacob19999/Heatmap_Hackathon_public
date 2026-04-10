"""Sanity checks for the full e2e pipeline outputs (MN + national presentation layer).

Run after run_dual_path_pipeline to validate tables, manifests, and product views.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Allow running from repo root or src
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline import config


def check_file(path: Path, label: str) -> bool:
    """Return True if path exists and is a file."""
    ok = path.is_file()
    print(f"  {'PASS' if ok else 'FAIL'}: {label} -> {path}")
    return ok


def sanity_check_tables() -> bool:
    """Verify required pipeline output tables exist and have expected schema."""
    tables_dir = config.TABLES_DIR
    all_ok = True

    print("\n--- Tables ---")
    # MN high-detail
    mn_access = tables_dir / "mn_high_detail_tract_access.parquet"
    mn_bei = tables_dir / "mn_high_detail_tract_bei.parquet"
    if not mn_access.exists():
        mn_access = tables_dir / "mn_mvp_tract_access.parquet"
    if not mn_bei.exists():
        mn_bei = tables_dir / "mn_mvp_tract_bei.parquet"
    all_ok &= check_file(mn_access, "MN tract access")
    all_ok &= check_file(mn_bei, "MN tract BEI")

    # USA county
    all_ok &= check_file(
        tables_dir / "usa_low_detail_county_county_access.parquet",
        "USA county access",
    )
    all_ok &= check_file(
        tables_dir / "usa_low_detail_county_county_bei.parquet",
        "USA county BEI",
    )

    # Cached inputs (used by pipeline when not using Valhalla)
    all_ok &= check_file(
        tables_dir / "valhalla_mn_hospitals_timedist.parquet",
        "MN travel-time matrix (cached)",
    )
    mn_filled = tables_dir / "valhalla_mn_hospitals_timedist_filled.parquet"
    if not mn_filled.exists():
        print(f"  (optional) MN filled matrix not found; raw will be used")
    all_ok &= check_file(
        tables_dir / "usa_low_detail_county_county_travel_time_matrix.parquet",
        "USA county travel-time matrix (cached)",
    )
    all_ok &= check_file(
        tables_dir / "usa_low_detail_county_county_origins.parquet",
        "USA county origins (cached)",
    )

    # Schema and row counts
    if mn_bei.exists():
        df = pd.read_parquet(mn_bei)
        cols = set(df.columns)
        id_col = "GEOID" if "GEOID" in cols else "tract_geoid"
        if id_col in cols:
            print(f"  MN tract BEI: {len(df):,} rows, id_col={id_col}")
        else:
            print(f"  WARN: MN tract BEI missing expected id column (GEOID/tract_geoid)")
    if (tables_dir / "usa_low_detail_county_county_bei.parquet").exists():
        df = pd.read_parquet(tables_dir / "usa_low_detail_county_county_bei.parquet")
        print(f"  USA county BEI: {len(df):,} rows, county_fips present={'county_fips' in df.columns}")

    return all_ok


def sanity_check_manifests() -> bool:
    """Verify product_views_manifest and profile manifests exist and reference valid paths."""
    manifests_dir = config.MANIFESTS_DIR
    output_dir = config.OUTPUT_DIR
    all_ok = True

    print("\n--- Manifests ---")
    product_path = manifests_dir / "product_views_manifest.json"
    all_ok &= check_file(product_path, "product_views_manifest.json")
    if not product_path.exists():
        return all_ok

    data = json.loads(product_path.read_text(encoding="utf-8"))
    views = data.get("views", [])
    if not views:
        print("  FAIL: product_views_manifest has no views")
        all_ok = False
    for v in views:
        view_id = v.get("view_id", "?")
        manifest_path = v.get("manifest_path")
        if not manifest_path:
            print(f"  FAIL: view {view_id} missing manifest_path")
            all_ok = False
            continue
        full = output_dir / manifest_path
        all_ok &= check_file(full, f"manifest for {view_id}")

    for profile_id in ("mn_high_detail", "usa_low_detail_county"):
        manifest_path = manifests_dir / f"{profile_id}_manifest.json"
        if not manifest_path.exists():
            manifest_path = manifests_dir / ("mn_mvp_manifest.json" if profile_id == "mn_high_detail" else manifest_path)
        all_ok &= check_file(manifest_path, f"profile manifest {profile_id}")

        if manifest_path.exists():
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            assets = m.get("assets", {})
            for level, scenarios in assets.items():
                for scenario, paths in scenarios.items():
                    for key in ("table", "access_table"):
                        rel = paths.get(key)
                        if rel:
                            full = output_dir / rel
                            if not full.exists():
                                print(f"  FAIL: asset {key} not found: {full}")
                                all_ok = False

    return all_ok


def sanity_check_geojson() -> bool:
    """Verify GeoJSON assets exist for frontend map."""
    geojson_dir = config.GEOJSON_DIR
    print("\n--- GeoJSON ---")
    ok1 = check_file(
        geojson_dir / "mn_high_detail_tract_bei_ground.geojson",
        "MN tract BEI GeoJSON",
    )
    ok2 = check_file(
        geojson_dir / "usa_low_detail_county_county_bei.geojson",
        "USA county BEI GeoJSON",
    )
    return ok1 and ok2


def sanity_check_bei_ranges() -> bool:
    """Optional: BEI and key columns in expected ranges."""
    tables_dir = config.TABLES_DIR
    all_ok = True
    print("\n--- BEI / value ranges ---")

    for label, path, id_col in [
        ("MN tract BEI", tables_dir / "mn_high_detail_tract_bei.parquet", "GEOID"),
        ("USA county BEI", tables_dir / "usa_low_detail_county_county_bei.parquet", "county_fips"),
    ]:
        if not path.exists() and "mn" in label.lower():
            path = tables_dir / "mn_mvp_tract_bei.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if id_col not in df.columns and "county" not in label:
            id_col = "tract_geoid"
        if "bei" not in df.columns:
            print(f"  WARN: {label} has no 'bei' column")
            continue
        bei = df["bei"].dropna()
        if len(bei) == 0:
            print(f"  WARN: {label} has no non-null BEI values")
            continue
        lo, hi = float(bei.min()), float(bei.max())
        in_range = 0 <= lo and hi <= 1.01  # allow tiny float overflow
        print(f"  {'PASS' if in_range else 'WARN'}: {label} BEI in [0,1]: min={lo:.4f}, max={hi:.4f} ({len(df):,} rows)")
        if not in_range:
            all_ok = False
    return all_ok


def main() -> int:
    print("Sanity check: full e2e pipeline outputs (MN + national, cached distance data)")
    t_ok = sanity_check_tables()
    m_ok = sanity_check_manifests()
    g_ok = sanity_check_geojson()
    b_ok = sanity_check_bei_ranges()
    all_ok = t_ok and m_ok and g_ok and b_ok
    print("\n--- Summary ---")
    print(f"  Tables:    {'PASS' if t_ok else 'FAIL'}")
    print(f"  Manifests: {'PASS' if m_ok else 'FAIL'}")
    print(f"  GeoJSON:   {'PASS' if g_ok else 'FAIL'}")
    print(f"  BEI range: {'PASS' if b_ok else 'WARN/FAIL'}")
    print(f"  Overall:   {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
