"""
Download external augmentation data: ACS, TIGER, RUCA, SVI (optional), FAA.
Run from repo root: python -m src.pipeline.download_external [--acs] [--tiger] [--ruca] [--svi] [--faa]
Or call download_all() from code.
"""
from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)

# Optional: Census API key for ACS (set CENSUS_API_KEY env var for large pulls)
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")

# TIGER 2025 tract shapefiles: one ZIP per state (FIPS 01-56)
# See: https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2025&layergroup=Census+Tracts
TIGER_BASE = "https://www2.census.gov/geo/tiger/TIGER2025/TRACT"
# Reserved FIPS (no Census data); 50 states + DC = 51 in-use codes
RESERVED_STATE_FIPS = {"03", "07", "14", "43", "52"}
STATE_FIPS = [f"{i:02d}" for i in range(1, 57)]
STATE_FIPS_DOWNLOAD = [f for f in STATE_FIPS if f not in RESERVED_STATE_FIPS]  # 51 codes for ACS/TIGER


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_acs(save_dir: Path | None = None) -> Path:
    """Download ACS 5-year 2022 tract-level B01003 (total pop) and B09001 (child pop); save to save_dir."""
    import requests
    import pandas as pd

    save_dir = save_dir or config.ACS_DIR
    _ensure_dir(save_dir)
    # Census API: 2022 ACS 5-year tract level (state-by-state to avoid timeout)
    base_url = "https://api.census.gov/data/2022/acs/acs5"
    get_vars = "NAME,B01003_001E,B09001_001E"
    params_base: dict = {"get": get_vars, "for": "tract:*"}
    if CENSUS_API_KEY:
        params_base["key"] = CENSUS_API_KEY

    rows: list[list] = []
    for st in STATE_FIPS_DOWNLOAD:
        r = None
        try:
            r = requests.get(base_url, params={**params_base, "in": f"state:{st}"}, timeout=120)
            r.raise_for_status()
            data = r.json()
            if not data:
                continue
            header = data[0]
            for rec in data[1:]:
                rows.append(rec)
        except Exception as e:
            print(f"ACS state {st} skipped: {e}")
            if r is not None:
                raw_preview = (r.text or "")[:1000]
                logger.warning(
                    "ACS state %s raw response: status=%s url=%s body_preview=%s",
                    st, r.status_code, r.url, raw_preview,
                )
                print(f"  [DEBUG] status={r.status_code} url={r.url}")
                print(f"  [DEBUG] body (first 500 chars): {raw_preview[:500]!r}")

    if not rows:
        raise RuntimeError("No ACS tract data retrieved. Check CENSUS_API_KEY and network.")

    df = pd.DataFrame(rows, columns=header)
    out_path = save_dir / "acs_2022_5yr_tract_b01003_b09001.csv"
    df.to_csv(out_path, index=False)
    n_states = df["state"].nunique() if "state" in df.columns else 0
    if n_states >= 50:
        print(f"ACS: {n_states} states combined into {out_path.name} (50 = success).")
    return out_path


def download_tiger(save_dir: Path | None = None, states: list[str] | None = None) -> list[Path]:
    """Download TIGER/Line 2025 tract shapefiles (one ZIP per state); save to save_dir."""
    import requests

    save_dir = save_dir or config.TIGER_DIR
    _ensure_dir(save_dir)
    states = states or STATE_FIPS_DOWNLOAD
    saved = []
    for fips in states:
        name = f"tl_2025_{fips}_tract.zip"
        url = f"{TIGER_BASE}/{name}"
        dest = save_dir / name
        if dest.exists():
            saved.append(dest)
            continue
        try:
            r = requests.get(url, timeout=120, stream=True)
            r.raise_for_status()
            dest.write_bytes(r.content)
            saved.append(dest)
        except Exception as e:
            print(f"TIGER {name} failed: {e}")
    n = len(saved)
    if n >= 50:
        print(f"TIGER 2025: {n} state tract files downloaded (50 = success).")
    return saved


def download_ruca(save_dir: Path | None = None) -> Path:
    """Use manually downloaded RUCA tract-level data. Place RUCA-codes-2020-tract.xlsx in save_dir.
    Download from: https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes/"""
    save_dir = save_dir or config.RUCA_DIR
    _ensure_dir(save_dir)
    dest = save_dir / config.RUCA_MANUAL_FILENAME
    if dest.exists():
        return dest
    print(
        f"RUCA: place {config.RUCA_MANUAL_FILENAME} in {save_dir}. "
        "Download from https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes/"
    )
    return save_dir


def download_svi(save_dir: Path | None = None) -> Path | None:
    """Optional: Download CDC/ATSDR SVI tract-level data. URL and format vary by year."""
    import requests

    save_dir = save_dir or config.SVI_DIR
    _ensure_dir(save_dir)
    # CDC SVI 2020 tract - example; replace with current year URL if needed
    url = "https://www.atsdr.cdc.gov/placeandhealth/svi/data_documentation_download.html"
    # Actual data is often a ZIP from a different URL; document manual step
    readme = save_dir / "README.txt"
    readme.write_text(
        "CDC/ATSDR SVI: Download from https://www.atsdr.cdc.gov/placeandhealth/svi/data_documentation_download.html\n"
        f"Place tract-level CSV here as {config.SVI_CSV_FILENAME} (pipeline uses FIPS, RPL_THEMES, RPL_THEME1-4).",
        encoding="utf-8",
    )
    return save_dir


# Expected manual FAA airport/heliport file (e.g. from 28-day subscription APT_BASE.csv)
FAA_APT_FILENAME = "APT_BASE.csv"


def download_faa(save_dir: Path | None = None) -> Path | None:
    """Use manually downloaded FAA airport/heliport data. Place APT_BASE.csv in save_dir.
    Export from FAA 28-day subscription (CSV_Data/*/APT_BASE.csv) or ADIP/catalog.data.faa.gov."""
    save_dir = save_dir or config.FAA_DIR
    _ensure_dir(save_dir)
    dest = save_dir / FAA_APT_FILENAME
    if dest.exists():
        return dest
    print(
        f"FAA: place {FAA_APT_FILENAME} in {save_dir}. "
        "Export from 28-day subscription or https://adip.faa.gov/agis/portal/"
    )
    return save_dir


def download_all(
    acs: bool = True,
    tiger: bool = True,
    ruca: bool = True,
    svi: bool = False,
    faa: bool = True,
) -> dict[str, object]:
    """Run selected downloads. Returns dict of step -> path or list of paths."""
    results = {}
    if acs:
        results["acs"] = download_acs()
    if tiger:
        results["tiger"] = download_tiger()
    if ruca:
        results["ruca"] = download_ruca()
    if svi:
        results["svi"] = download_svi()
    if faa:
        results["faa"] = download_faa()
    return results


def _main() -> None:
    import argparse
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    p = argparse.ArgumentParser(description="Download external data for BEI pipeline")
    p.add_argument("--acs", action="store_true", default=True, help="Download ACS tract population")
    p.add_argument("--no-acs", action="store_false", dest="acs")
    p.add_argument("--tiger", action="store_true", default=True, help="Download TIGER tract shapefiles")
    p.add_argument("--no-tiger", action="store_false", dest="tiger")
    p.add_argument("--ruca", action="store_true", default=True, help="Download RUCA codes")
    p.add_argument("--no-ruca", action="store_false", dest="ruca")
    p.add_argument("--svi", action="store_true", help="Optional: download SVI")
    p.add_argument("--faa", action="store_true", default=True, help="Download FAA airport/heliport data")
    p.add_argument("--no-faa", action="store_false", dest="faa")
    args = p.parse_args()
    download_all(acs=args.acs, tiger=args.tiger, ruca=args.ruca, svi=args.svi, faa=args.faa)
    print("Download steps completed. Check Data/external/* for outputs.")


if __name__ == "__main__":
    _main()
