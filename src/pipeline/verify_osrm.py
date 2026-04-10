"""Verify OSRM server is running and responding. Used after T011 setup."""
from __future__ import annotations

import sys

from . import config


def verify_osrm(base_url: str | None = None) -> bool:
    """Check OSRM health and run a minimal table query. Returns True if OK."""
    import requests

    base_url = base_url or config.OSRM_BASE_URL
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        if r.status_code != 200:
            print(f"OSRM health returned {r.status_code}")
            return False
        # Optional: tiny table query (two coordinates)
        table_url = f"{base_url}{config.OSRM_TABLE_SERVICE}"
        params = {
            "coordinates": "-77.0369,38.9072;-122.4194,37.7749",
            "annotations": "duration",
        }
        r2 = requests.get(table_url, params=params, timeout=10)
        if r2.status_code != 200:
            print(f"OSRM table query returned {r2.status_code}")
            return False
        print("OSRM server OK (health + table query).")
        return True
    except Exception as e:
        print(f"OSRM verification failed: {e}")
        return False


if __name__ == "__main__":
    ok = verify_osrm()
    sys.exit(0 if ok else 1)
