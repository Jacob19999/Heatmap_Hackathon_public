"""
Facility geocoding: two-stage (ZIP centroid first, Census Geocoder batch refinement),
spatial join to TIGER tract boundaries for tract_geoid assignment.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from . import config

LOG = logging.getLogger(__name__)
# Census batch: https://geocoding.geo.census.gov/geocoder/geographies/addressbatch (max 10k records, 5MB)
CENSUS_BATCH_URL = "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch"
CENSUS_BATCH_BENCHMARK = "Public_AR_Current"
CENSUS_BATCH_VINTAGE = "Current_Current"


def _address_for_geocoder(row: pd.Series) -> str:
    """Build single-line address for Census batch."""
    parts = [
        str(row.get("ADDRESS", "") or "").strip(),
        str(row.get("CITY", "") or "").strip(),
        str(row.get("STATE", "") or "").strip(),
        str(row.get("ZIP_CODE", "") or "").strip(),
    ]
    return ", ".join(p for p in parts if p)


def write_batch_upload_file(
    facilities: pd.DataFrame,
    path: Path | None = None,
    id_col: str = "AHA_ID",
) -> Path:
    """Write CSV for manual upload to Census batch geocoder.
    Upload at: https://geocoding.geo.census.gov/geocoder/geographies/addressbatch
    Format: Unique_ID, Street address, City, State, Zip (max 10,000 records, 5MB)."""
    path = path or (config.TABLES_DIR / "census_batch_upload.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["Unique_ID,Street address,City,State,Zip"]
    for i, (_, row) in enumerate(facilities.iterrows()):
        uid = row.get(id_col, i)
        street = (row.get("ADDRESS") or "").strip() or ""
        city = (row.get("CITY") or "").strip() or ""
        state = (row.get("STATE") or "").strip() or ""
        zip_ = str(row.get("ZIP_CODE") or "").strip() or ""
        lines.append(f'{uid},"{street}","{city}","{state}","{zip_}"')
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _normalize_tract_geoid(geoid: str) -> str:
    """Normalize tract GEOID to 11-digit FIPS (state 2 + county 3 + tract 6)."""
    if not geoid or (isinstance(geoid, float) and pd.isna(geoid)):
        return ""
    s = str(geoid).strip().replace(".0", "")
    if not s or not s.isdigit():
        return ""
    if len(s) >= 11:
        return s[:11].zfill(11)
    return s.zfill(11)


def load_batch_results_and_merge(
    facilities: pd.DataFrame,
    results_path: Path | None = None,
    id_col: str = "AHA_ID",
) -> pd.DataFrame:
    """Load Census batch geocoder result CSV and merge latitude, longitude, tract_geoid into facilities.
    Expects GeocodeResults.csv columns: Unique_ID, Long, Lat, and state/county/tract in positions 10/11/12
    or columns named State FIPS, County FIPS, Tract. Only overwrites missing coords/tract; preserves
    existing non-empty tract_geoid. Normalizes tract_geoid to 11-digit FIPS."""
    results_path = results_path or (config.TABLES_DIR / "GeocodeResults.csv")
    if not results_path.exists():
        raise FileNotFoundError(f"Census batch results not found: {results_path}")
    df = pd.read_csv(results_path)
    id_key = "Unique_ID"
    lon_col = "Long"
    lat_col = "Lat"
    if id_key not in df.columns or lon_col not in df.columns or lat_col not in df.columns:
        raise ValueError(
            f"Results CSV must have columns {id_key!r}, {lon_col!r}, {lat_col!r}. Found: {list(df.columns)}"
        )
    out = facilities.copy()
    if "latitude" not in out.columns:
        out["latitude"] = float("nan")
    if "longitude" not in out.columns:
        out["longitude"] = float("nan")
    if "tract_geoid" not in out.columns:
        out["tract_geoid"] = ""
    if "geocode_method" not in out.columns:
        out["geocode_method"] = ""
    # State FIPS, County FIPS, Tract: by position (Census batch) or by name
    state_col = None
    county_col = None
    tract_col = None
    for c in df.columns:
        c_lower = str(c).lower()
        if "state" in c_lower and "fips" in c_lower:
            state_col = c
        elif "county" in c_lower and "fips" in c_lower:
            county_col = c
        elif c_lower == "tract" or ("tract" in c_lower and "fips" not in c_lower):
            tract_col = c
    if state_col is None and len(df.columns) > 10:
        state_col = df.columns[10]
    if county_col is None and len(df.columns) > 11:
        county_col = df.columns[11]
    if tract_col is None and len(df.columns) > 12:
        tract_col = df.columns[12]
    for _, row in df.iterrows():
        uid = row[id_key]
        idx = out[out[id_col].astype(str) == str(uid)].index
        if len(idx) == 0:
            continue
        idx = idx[0]
        lon = row[lon_col]
        lat = row[lat_col]
        existing_tract = out.loc[idx, "tract_geoid"]
        has_existing_tract = isinstance(existing_tract, str) and existing_tract.strip() != "" and not (isinstance(existing_tract, float) and pd.isna(existing_tract))
        if pd.notna(lon) and pd.notna(lat):
            out.loc[idx, "longitude"] = float(lon)
            out.loc[idx, "latitude"] = float(lat)
        geoid = ""
        if state_col and county_col and tract_col:
            s = row.get(state_col)
            c = row.get(county_col)
            t = row.get(tract_col)
            if pd.notna(s) and pd.notna(c) and pd.notna(t):
                try:
                    geoid = _normalize_tract_geoid(f"{int(float(s)):02d}{int(float(c)):03d}{int(float(t)):06d}")
                except (ValueError, TypeError):
                    geoid = ""
        if geoid and not has_existing_tract:
            out.loc[idx, "tract_geoid"] = geoid
        if geoid or (pd.notna(lon) and pd.notna(lat)):
            if out.loc[idx, "geocode_method"] == "" or pd.isna(out.loc[idx, "geocode_method"]):
                out.loc[idx, "geocode_method"] = "census_batch_manual"
    return out


def geocode_with_census_batch(
    df: pd.DataFrame,
    id_col: str = "AHA_ID",
    batch_size: int = 1000,
) -> pd.DataFrame:
    """Call Census batch geocoder; return df with columns latitude, longitude, tract_geoid, geocode_method."""
    import requests

    out = df.copy()
    if "latitude" not in out.columns:
        out["latitude"] = float("nan")
    if "longitude" not in out.columns:
        out["longitude"] = float("nan")
    if "tract_geoid" not in out.columns:
        out["tract_geoid"] = ""
    if "geocode_method" not in out.columns:
        out["geocode_method"] = ""

    n_chunks = (len(out) + batch_size - 1) // batch_size
    from tqdm.auto import tqdm
    for start in tqdm(
        range(0, len(out), batch_size),
        total=n_chunks,
        desc="Census batch",
        unit="chunk",
        leave=True,
    ):
        chunk_idx = start // batch_size + 1
        batch = out.iloc[start : start + batch_size]
        tqdm.write(f"  Current: chunk {chunk_idx}/{n_chunks} (rows {start + 1}-{min(start + batch_size, len(out))})")
        lines = ["Unique_ID,Street address,City,State,Zip"]
        for i, (_, row) in enumerate(batch.iterrows()):
            uid = row.get(id_col, start + i)
            street = (row.get("ADDRESS") or "").strip() or ""
            city = (row.get("CITY") or "").strip() or ""
            state = (row.get("STATE") or "").strip() or ""
            zip_ = str(row.get("ZIP_CODE") or "").strip() or ""
            lines.append(f'{uid},"{street}","{city}","{state}","{zip_}"')
        payload = "\n".join(lines)
        try:
            r = requests.post(
                CENSUS_BATCH_URL,
                data={"benchmark": CENSUS_BATCH_BENCHMARK, "vintage": CENSUS_BATCH_VINTAGE},
                files={"batchFile": ("batch.csv", payload.encode("utf-8") if isinstance(payload, str) else payload, "text/csv")},
                timeout=120,
            )
            r.raise_for_status()
            # Parse CSV response: Unique_ID, Input address, Match?, Match type, ..., State FIPS, County FIPS, Tract
            resp_lines = r.text.strip().split("\n")
            if len(resp_lines) < 2:
                continue
            header = resp_lines[0]
            chunk_matches = 0
            for line in resp_lines[1:]:
                parts = line.split(",")
                if len(parts) < 15:
                    continue
                try:
                    uid = parts[0].strip('"')
                    lat = float(parts[9].strip('"')) if parts[9].strip('"') else float("nan")
                    lon = float(parts[10].strip('"')) if parts[10].strip('"') else float("nan")
                    state_fips = parts[11].strip('"') if len(parts) > 11 else ""
                    county_fips = parts[12].strip('"') if len(parts) > 12 else ""
                    tract = parts[13].strip('"') if len(parts) > 13 else ""
                    geoid = (state_fips + county_fips + tract) if (state_fips and county_fips and tract) else ""
                    idx = out[out[id_col].astype(str) == str(uid)].index
                    if len(idx) > 0:
                        out.loc[idx[0], "latitude"] = lat
                        out.loc[idx[0], "longitude"] = lon
                        out.loc[idx[0], "tract_geoid"] = geoid
                        out.loc[idx[0], "geocode_method"] = "census_batch"
                        if geoid:
                            chunk_matches += 1
                except (IndexError, ValueError):
                    pass
            tqdm.write(f"    -> {chunk_matches} matched in this chunk")
        except Exception as e:
            LOG.warning("Census batch chunk failed: %s", e)
            # Use ASCII-only output for Windows console compatibility
            tqdm.write(f"    -> batch failed: {e}")
        time.sleep(0.2)
    return out


CENSUS_SINGLE_URL = "https://geocoding.geo.census.gov/geocoder/geographies/address"


def fill_coords_from_census_single(
    df: pd.DataFrame,
    id_col: str = "AHA_ID",
) -> pd.DataFrame:
    """When batch fails, fill latitude/longitude via Census single-address API (City, State ZIP)."""
    import requests

    out = df.copy()
    missing = out["latitude"].isna() | out["longitude"].isna()
    if not missing.any():
        return out
    # Group by (CITY, STATE, ZIP_CODE) to minimize API calls
    keys = out.loc[missing].apply(
        lambda r: (str(r.get("CITY") or "").strip(), str(r.get("STATE") or "").strip(), str(r.get("ZIP_CODE") or "").strip()),
        axis=1,
    )
    unique_keys = [k for k in keys.unique() if (k[0] or k[1] or k[2]) and (f"{k[0]}, {k[1]} {k[2]}".strip(", "))]
    n_unique = len(unique_keys)
    from tqdm.auto import tqdm
    print(f"  Single-address fallback: {missing.sum()} rows missing coords, {n_unique} unique City/State/ZIP to look up...")
    cache = {}
    it = tqdm(unique_keys, desc="Census single", unit="addr", leave=True)
    for i, (city, state, zip_) in enumerate(it):
        if not (city or state or zip_):
            continue
        addr = f"{city}, {state} {zip_}".strip(", ")
        if not addr.strip():
            continue
        it.set_postfix_str(addr[:50] + ("..." if len(addr) > 50 else ""))
        try:
            r = requests.get(
                CENSUS_SINGLE_URL,
                params={"address": addr, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("result", {}).get("addressMatches"):
                m = data["result"]["addressMatches"][0]
                coords = m.get("coordinates", {})
                cache[(city, state, zip_)] = (coords.get("y"), coords.get("x"))
            time.sleep(0.15)
        except Exception as e:
            LOG.debug("Census single %s: %s", addr[:50], e)
    filled = 0
    for idx in out.index[missing]:
        row = out.loc[idx]
        k = (str(row.get("CITY") or "").strip(), str(row.get("STATE") or "").strip(), str(row.get("ZIP_CODE") or "").strip())
        if k in cache:
            lat, lon = cache[k]
            if lat is not None and lon is not None:
                out.loc[idx, "latitude"] = lat
                out.loc[idx, "longitude"] = lon
                if out.loc[idx, "geocode_method"] == "" or pd.isna(out.loc[idx, "geocode_method"]):
                    out.loc[idx, "geocode_method"] = "census_single_zip"
                filled += 1
    print(f"    -> filled coordinates for {filled} rows")
    return out


def assign_tract_from_tiger(facilities: pd.DataFrame, tiger_dir: Path | None = None) -> pd.DataFrame:
    """Where latitude/longitude exist but tract_geoid missing, do point-in-polygon with TIGER shapefiles."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        return facilities
    tiger_dir = tiger_dir or config.TIGER_DIR
    shp_files = list(tiger_dir.glob("tl_2025_*_tract.shp"))
    if not shp_files:
        LOG.warning("No TIGER tract shapefiles in %s; skipping tract assignment.", tiger_dir)
        print("  TIGER: no shapefiles found; skipping tract assignment.")
        return facilities
    from tqdm.auto import tqdm
    print(f"  TIGER: loading {len(shp_files)} tract shapefiles...")
    gdf_tracts = []
    it = tqdm(shp_files, desc="TIGER load", unit="shp", leave=True)
    for shp in it:
        try:
            it.set_postfix_str(shp.name)
            g = gpd.read_file(shp)
            g = g.to_crs("EPSG:4326")
            if "GEOID" in g.columns:
                gdf_tracts.append(g[["GEOID", "geometry"]])
        except Exception as e:
            LOG.warning("TIGER read %s: %s", shp, e)
    if not gdf_tracts:
        return facilities
    tracts = gpd.GeoDataFrame(pd.concat(gdf_tracts, ignore_index=True))
    out = facilities.copy()
    mask = out["latitude"].notna() & out["longitude"].notna() & (out["tract_geoid"].isna() | (out["tract_geoid"] == ""))
    if not mask.any():
        return out
    pts = gpd.GeoDataFrame(
        geometry=[Point(lon, lat) for lon, lat in zip(out.loc[mask, "longitude"], out.loc[mask, "latitude"])],
        index=out.index[mask],
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(pts, tracts, how="left", predicate="within")
    assigned = 0
    for idx in joined.index.unique():
        geoid = joined.loc[idx, "GEOID"].iloc[0] if isinstance(joined.loc[idx, "GEOID"], (pd.Series,)) else joined.loc[idx, "GEOID"]
        if pd.notna(geoid):
            out.loc[idx, "tract_geoid"] = str(geoid)
            if out.loc[idx, "geocode_method"] == "" or pd.isna(out.loc[idx, "geocode_method"]):
                out.loc[idx, "geocode_method"] = "zip_centroid_tiger"
            assigned += 1
    print(f"  TIGER: assigned tract for {assigned} facilities (point-in-polygon)")
    return out


def geocode_facilities(
    facilities: pd.DataFrame,
    use_census_batch: bool = True,
    use_tiger_for_missing: bool = True,
) -> pd.DataFrame:
    """Two-stage: Census batch then TIGER point-in-polygon for missing. Adds latitude, longitude, tract_geoid, geocode_method.
    When Census batch fails (e.g. 500), falls back to single-address API by City/State/ZIP then TIGER tract assignment."""
    n = len(facilities)
    print(f"Geocoding {n} facilities...")
    if use_census_batch:
        print("Step 1: Census batch geocoder")
        facilities = geocode_with_census_batch(facilities)
        with_coords = (facilities["latitude"].notna() & facilities["longitude"].notna()).sum()
        with_tract = (facilities["tract_geoid"].notna() & (facilities["tract_geoid"] != "")).sum()
        # ASCII-only for Windows consoles
        print(f"  -> {with_coords} with coordinates, {with_tract} with tract from batch")
    # If many rows still lack coords (e.g. batch failed), try single-address API by City/State/ZIP
    missing_coords = facilities["latitude"].isna() | facilities["longitude"].isna()
    if missing_coords.any() and missing_coords.sum() > 10:
        print(f"Step 2: Single-address fallback ({missing_coords.sum()} rows missing coords)")
        LOG.info("Census batch left %d rows without coordinates; trying single-address fallback.", missing_coords.sum())
        facilities = fill_coords_from_census_single(facilities)
    else:
        print("Step 2: Single-address fallback (skipped — few or no missing coords)")
    if use_tiger_for_missing:
        print("Step 3: TIGER tract assignment (point-in-polygon)")
        facilities = assign_tract_from_tiger(facilities)
    n = len(facilities)
    with_tract = (facilities["tract_geoid"].notna() & (facilities["tract_geoid"] != "")).sum()
    match_rate = with_tract / n * 100 if n else 0
    print(f"Done: {with_tract}/{n} facilities with tract ({match_rate:.1f}%)")
    print_missing_tract_facilities(facilities)
    LOG.info("Geocode match rate: %.1f%% (%d / %d)", match_rate, int(with_tract), n)
    return facilities


def print_missing_tract_facilities(facilities: pd.DataFrame) -> None:
    """Print facilities that have no tract_geoid (for debugging)."""
    missing = facilities[facilities["tract_geoid"].isna() | (facilities["tract_geoid"] == "")]
    if len(missing) == 0:
        return
    id_col = "AHA_ID" if "AHA_ID" in missing.columns else missing.columns[0]
    name_col = next((c for c in ["FACILITY_NAME", "NAME", "HOSPITAL_NAME", "ARPT_NAME"] if c in missing.columns), None)
    for _, row in missing.iterrows():
        parts = [f"  {id_col}={row.get(id_col)}"]
        if name_col:
            parts.append(f" {name_col}={row.get(name_col)}")
        if "CITY" in missing.columns and "STATE" in missing.columns:
            parts.append(f" {row.get('CITY')}, {row.get('STATE')}")
        print("Missing tract:", ", ".join(str(p) for p in parts))
