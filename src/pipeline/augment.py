"""
Augmentation: load TIGER tract geometry, join ACS population (B01003, B09001), RUCA, optional SVI.
Produces tract-level analytic table with total_pop, child_pop, ruca_code, is_rural, geometry.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import config

LOG = logging.getLogger(__name__)


def load_tiger_tracts(tiger_dir: Path | None = None) -> "pd.DataFrame":
    """Load TIGER/Line 2025 tract shapefiles; return GeoDataFrame with GEOID, geometry, centroid."""
    import geopandas as gpd
    from tqdm.auto import tqdm

    tiger_dir = tiger_dir or config.TIGER_DIR
    shp_files = list(tiger_dir.glob("tl_2025_*_tract.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No TIGER tract shapefiles in {tiger_dir}")
    gdfs = []
    it = tqdm(shp_files, desc="Augment TIGER", unit="shp", leave=True)
    for shp in it:
        it.set_postfix_str(shp.name)
        g = gpd.read_file(shp)
        g = g.to_crs("EPSG:4326")
        if "GEOID" not in g.columns and "TRACTCE" in g.columns and "STATEFP" in g.columns and "COUNTYFP" in g.columns:
            g["GEOID"] = g["STATEFP"].astype(str) + g["COUNTYFP"].astype(str) + g["TRACTCE"].astype(str)
        gdfs.append(g)
    gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
    if "INTPTLAT" in gdf.columns and "INTPTLON" in gdf.columns:
        gdf["centroid_lat"] = pd.to_numeric(gdf["INTPTLAT"], errors="coerce")
        gdf["centroid_lon"] = pd.to_numeric(gdf["INTPTLON"], errors="coerce")
    else:
        gdf["centroid_lat"] = gdf.geometry.centroid.y
        gdf["centroid_lon"] = gdf.geometry.centroid.x
    return gdf


def load_acs_tract(acs_dir: Path | None = None) -> pd.DataFrame:
    """Load ACS 2022 5yr tract B01003, B09001 from download_external output."""
    acs_dir = Path(acs_dir or config.ACS_DIR)
    candidates = list(acs_dir.glob("acs_2022*.csv")) + list(acs_dir.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No ACS tract CSV in {acs_dir}")
    df = pd.read_csv(candidates[0])
    # Census API returns state, county, tract; build 11-digit GEOID (SS CCC TTTTTT)
    if "state" in df.columns and "county" in df.columns and "tract" in df.columns:
        tract_str = df["tract"].astype(str).str.replace(r"\.0$", "", regex=True)
        df["GEOID"] = (
            df["state"].astype(str).str.zfill(2)
            + df["county"].astype(str).str.zfill(3)
            + tract_str.str.zfill(6)
        )
    elif "GEOID" not in df.columns and "geoid" in df.columns:
        df["GEOID"] = df["geoid"]
    df = df.rename(columns={"B01003_001E": "total_pop", "B09001_001E": "child_pop"})
    for col in ("total_pop", "child_pop"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def _apply_ruca_columns(df: pd.DataFrame) -> None:
    """Identify GEOID and ruca_code columns by name and rename in place."""
    cols = [c for c in df.columns if "fips" in c.lower() or "tract" in c.lower() or c == "GEOID"]
    geoid_col = cols[0] if cols else df.columns[0]
    ruca_cols = [c for c in df.columns if "ruca" in c.lower()]
    ruca_col = ruca_cols[0] if ruca_cols else df.columns[1]
    df.rename(columns={geoid_col: "GEOID", ruca_col: "ruca_code"}, inplace=True)


def load_ruca(ruca_dir: Path | None = None) -> pd.DataFrame:
    """Load RUCA tract-level; expect column for tract GEOID and primary RUCA code.
    Supports RUCA-codes-2020-tract.xlsx (manual download) or any *.csv in ruca_dir."""
    ruca_dir = Path(ruca_dir or config.RUCA_DIR)
    xlsx_path = ruca_dir / config.RUCA_MANUAL_FILENAME
    if xlsx_path.exists():
        # Sheet has a title row; real headers are in row 1 (0-indexed header=1)
        df = pd.read_excel(xlsx_path, sheet_name="RUCA2020 Tract Data", header=1)
        # Prefer 2020 tract FIPS and primary RUCA for ERS 2020 file
        if "TractFIPS20" in df.columns and "PrimaryRUCA" in df.columns:
            df = df.rename(columns={"TractFIPS20": "GEOID", "PrimaryRUCA": "ruca_code"})
        else:
            _apply_ruca_columns(df)
    else:
        candidates = list(ruca_dir.glob("*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"No RUCA file in {ruca_dir}. Place {config.RUCA_MANUAL_FILENAME} or a RUCA CSV there."
            )
        df = pd.read_csv(candidates[0])
        _apply_ruca_columns(df)
    df["GEOID"] = df["GEOID"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    df["ruca_code"] = pd.to_numeric(df["ruca_code"], errors="coerce")
    # Exclude non-standard code 99 (not coded / water) from forcing rural
    return df[["GEOID", "ruca_code"]].dropna(subset=["ruca_code"]).query("ruca_code != 99")


# CDC/ATSDR SVI column mapping: CSV column -> data-model name
SVI_CSV_TO_MODEL = {
    "RPL_THEMES": "svi_overall",
    "RPL_THEME1": "svi_theme1",
    "RPL_THEME2": "svi_theme2",
    "RPL_THEME3": "svi_theme3",
    "RPL_THEME4": "svi_theme4",
}


def load_svi(svi_dir: Path | None = None) -> pd.DataFrame | None:
    """Load CDC/ATSDR SVI tract-level data from CSV (e.g. SVI_2022_US.csv).

    Expects FIPS (11-digit tract GEOID) and RPL_THEMES, RPL_THEME1..4.
    Returns a DataFrame with GEOID and svi_overall, svi_theme1..4, or None if not found.
    """
    svi_dir = Path(svi_dir or config.SVI_DIR)
    path = svi_dir / config.SVI_CSV_FILENAME
    if not path.exists():
        candidates = list(svi_dir.glob("*.csv"))
        path = candidates[0] if candidates else None
    if path is None or not path.exists():
        LOG.debug("No SVI CSV in %s; skipping SVI overlay.", svi_dir)
        return None
    df = pd.read_csv(path, dtype=str, low_memory=False)
    # FIPS may be named FIPS or GEOID
    geoid_col = "FIPS" if "FIPS" in df.columns else "GEOID"
    if geoid_col not in df.columns:
        LOG.warning("SVI CSV %s has no FIPS/GEOID column; skipping.", path)
        return None
    df["GEOID"] = df[geoid_col].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    model_cols = []
    for csv_col, model_name in SVI_CSV_TO_MODEL.items():
        if csv_col in df.columns:
            df[model_name] = pd.to_numeric(df[csv_col], errors="coerce")
            model_cols.append(model_name)
    if not model_cols:
        LOG.warning("SVI CSV %s has no RPL_THEMES/RPL_THEME1-4 columns; skipping.", path)
        return None
    out = df[["GEOID"] + model_cols].drop_duplicates("GEOID")
    LOG.info("Loaded SVI for %d tracts from %s", len(out), path.name)
    return out


def augment_tracts(
    tiger_gdf: "pd.DataFrame",
    acs_df: pd.DataFrame | None = None,
    ruca_df: pd.DataFrame | None = None,
    svi_df: pd.DataFrame | None = None,
) -> "pd.DataFrame":
    """Join ACS, RUCA, and optional SVI to tract geometry. Derive is_rural (ruca_code >= 4).
    Guarantees output has total_pop, child_pop, ruca_code, is_rural, centroid_lat, centroid_lon
    (population and centroid non-null; RUCA null where not joined). Optional svi_overall, svi_theme1..4."""
    gdf = tiger_gdf.copy()
    if acs_df is not None and "GEOID" in gdf.columns:
        acs_sub = acs_df[["GEOID", "total_pop", "child_pop"]].drop_duplicates("GEOID")
        gdf = gdf.merge(acs_sub, on="GEOID", how="left")
    if "total_pop" not in gdf.columns:
        gdf["total_pop"] = 0
    if "child_pop" not in gdf.columns:
        gdf["child_pop"] = 0
    gdf["total_pop"] = pd.to_numeric(gdf["total_pop"], errors="coerce").fillna(0).astype(int)
    gdf["child_pop"] = pd.to_numeric(gdf["child_pop"], errors="coerce").fillna(0).astype(int)
    if ruca_df is not None and "GEOID" in gdf.columns:
        gdf = gdf.merge(ruca_df, on="GEOID", how="left")
    if svi_df is not None and "GEOID" in gdf.columns:
        gdf = gdf.merge(svi_df, on="GEOID", how="left")
    if "ruca_code" not in gdf.columns:
        gdf["ruca_code"] = float("nan")
    else:
        gdf["ruca_code"] = pd.to_numeric(gdf["ruca_code"], errors="coerce")
    gdf["is_rural"] = gdf["ruca_code"].fillna(0) >= 4
    if "centroid_lat" not in gdf.columns and "geometry" in gdf.columns:
        gdf["centroid_lat"] = gdf.geometry.centroid.y
    if "centroid_lon" not in gdf.columns and "geometry" in gdf.columns:
        gdf["centroid_lon"] = gdf.geometry.centroid.x
    return gdf


def build_analytic_table(
    facilities: pd.DataFrame,
    tiger_dir: Path | None = None,
    acs_dir: Path | None = None,
    ruca_dir: Path | None = None,
    svi_dir: Path | None = None,
) -> "pd.DataFrame":
    """Build tract-level analytic table: TIGER + ACS + RUCA + optional SVI."""
    from tqdm.auto import tqdm

    tiger_dir = tiger_dir or config.TIGER_DIR
    acs_dir = acs_dir or config.ACS_DIR
    ruca_dir = ruca_dir or config.RUCA_DIR
    svi_dir = svi_dir or config.SVI_DIR
    with tqdm(total=5, desc="Augment", unit="step", leave=True) as pbar:
        pbar.set_postfix_str("current: load TIGER tracts")
        tiger = load_tiger_tracts(tiger_dir)
        pbar.update(1)
        pbar.set_postfix_str("current: load ACS")
        acs = None
        acs_path = Path(acs_dir) / "acs_2022_5yr_tract_b01003_b09001.csv"
        if acs_path.exists():
            try:
                acs = load_acs_tract(acs_dir)
            except Exception as e:
                LOG.warning("ACS load failed: %s", e)
        pbar.update(1)
        pbar.set_postfix_str("current: load RUCA")
        ruca = None
        try:
            ruca = load_ruca(ruca_dir)
        except Exception as e:
            LOG.warning("RUCA load failed: %s", e)
        pbar.update(1)
        pbar.set_postfix_str("current: load SVI")
        svi = None
        try:
            svi = load_svi(svi_dir)
        except Exception as e:
            LOG.warning("SVI load failed: %s", e)
        pbar.update(1)
        pbar.set_postfix_str("current: merge tracts")
        analytic = augment_tracts(tiger, acs, ruca, svi)
        pbar.set_postfix_str(f"done: {len(analytic)} tracts")
        pbar.update(1)
    LOG.info("Analytic table: %d tracts", len(analytic))
    return analytic
