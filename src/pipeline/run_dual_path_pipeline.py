"""Run the full dual-path pipeline: MN high-detail (tract) + USA low-detail (county).

Uses:
  - MN travel time matrix (valhalla_mn_hospitals_timedist.parquet / _filled)
  - USA county travel time matrix (usa_low_detail_county_county_travel_time_matrix.parquet)

Then writes product_views_manifest.json for the frontend.
"""
from __future__ import annotations

import logging

from .export import write_default_dual_path_product_views_manifest
from .mn_mvp_pipeline import run_mn_pipeline
from .usa_low_detail_county import run_usa_county_pipeline_from_matrix

LOG = logging.getLogger(__name__)


def run_full_dual_path_pipeline() -> None:
    """Run MN pipeline, USA county pipeline from matrix, and product views manifest."""
    LOG.info("Running MN high-detail pipeline (tract-level, MN matrix) …")
    run_mn_pipeline("mn_high_detail")

    LOG.info("Running USA low-detail county pipeline (county matrix) …")
    run_usa_county_pipeline_from_matrix()

    LOG.info("Writing product views manifest …")
    write_default_dual_path_product_views_manifest()
    LOG.info("Full dual-path pipeline complete.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_full_dual_path_pipeline()
    print("Dual-path pipeline complete. MN tract + USA county access/BEI and manifests written.")


if __name__ == "__main__":
    main()
