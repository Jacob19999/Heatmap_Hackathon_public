from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import requests

from .run_valhalla_matrix import build_inputs
from . import config


def main() -> None:
    matrix_path = Path("Data/output/tables/valhalla_sample_500.parquet")
    if not matrix_path.exists():
        raise FileNotFoundError(f"{matrix_path} not found. Run the 500-origin sample first.")

    df = pd.read_parquet(matrix_path)
    tracts, facilities = build_inputs()
    tracts = tracts.rename(columns={"GEOID": "tract_geoid"})

    inf_df = df[df["duration_min"] == float("inf")].copy()
    print(f"Total inf rows: {len(inf_df)}")

    sample_size = min(20, len(inf_df))
    if sample_size == 0:
        print("No inf rows to inspect.")
        return

    sample_inf = inf_df.sample(sample_size, random_state=42)

    tracts_idx = tracts.set_index("tract_geoid")
    facilities_idx = facilities.set_index("AHA_ID")

    base_url = config.VALHALLA_BASE_URL.rstrip("/")
    route_url = f"{base_url}/route"

    for idx, (_, row) in enumerate(sample_inf.iterrows()):
        o_id = row["origin_id"]
        d_id = row["destination_id"]
        print("\n========================================")
        print(f"[{idx}] Origin {o_id} -> Dest {d_id}")

        try:
            o = tracts_idx.loc[o_id]
            d = facilities_idx.loc[d_id]
        except KeyError:
            print("  [SKIP] Missing coords for origin or dest")
            continue

        print(f"  origin: ({o['centroid_lat']}, {o['centroid_lon']})")
        print(f"  dest  : ({d['latitude']}, {d['longitude']})")

        payload = {
            "locations": [
                {"lat": float(o["centroid_lat"]), "lon": float(o["centroid_lon"])},
                {"lat": float(d["latitude"]), "lon": float(d["longitude"])},
            ],
            "costing": "auto",
            "units": "kilometers",
        }

        try:
            r = requests.post(route_url, json=payload, timeout=30)
            status = r.status_code
            text = (r.text or "").strip()
            try:
                data = r.json()
                error = data.get("error") or data.get("message") or ""
            except Exception:
                error = ""
            print(f"  HTTP status: {status}")
            if error:
                print(f"  Valhalla error: {error}")
            else:
                print(f"  Raw body (first 200 chars): {text[:200]}")
        except Exception as exc:
            print(f"  Request failed: {exc}")


if __name__ == "__main__":
    main()

