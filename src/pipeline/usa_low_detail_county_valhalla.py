"""USA low-detail (county-centroid) Valhalla routing pipeline.

Builds county-level routing origins from the tract analytic table, then uses
Valhalla to compute a county -> hospital travel-time matrix suitable for the
`usa_low_detail_county` dataset profile.
"""
from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config
from .aggregation import validate_county_only_profile
from .presentation_scope import get_profile
from .routing import compute_travel_time_matrix
from .routing_inputs import build_county_origins as build_county_origins_core
from .routing_inputs import build_facilities

LOG = logging.getLogger(__name__)
# Keep each chunk small enough to stay under ~100 Valhalla requests (avoids OOM).
DEFAULT_COUNTY_CHUNK_SIZE = 100
COUNTY_ORIGINS_CACHE_PATH = config.TABLES_DIR / "usa_low_detail_county_county_origins.parquet"


def build_county_origins(pop_col: str = "total_pop", force_rebuild: bool = False) -> pd.DataFrame:
    """Build or load cached county-level routing origins (uses shared builder from routing_inputs)."""
    out_path = COUNTY_ORIGINS_CACHE_PATH
    if out_path.exists() and not force_rebuild:
        LOG.info("Using cached county origins from %s", out_path)
        counties = pd.read_parquet(out_path)
        LOG.info("Loaded %d cached county origins.", len(counties))
        return counties

    counties = build_county_origins_core(pop_col=pop_col)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counties.to_parquet(out_path, index=False)
    LOG.info("County origins table written to %s (%d counties).", out_path, len(counties))
    return counties


def _iter_origin_chunks(origins: pd.DataFrame, chunk_size: int) -> tuple[int, pd.DataFrame]:
    for start in range(0, len(origins), chunk_size):
        stop = min(start + chunk_size, len(origins))
        yield start // chunk_size + 1, origins.iloc[start:stop].copy()


def _restart_valhalla_and_wait(
    container_name: str,
    base_url: str | None = None,
    timeout_seconds: int = 90,
    poll_interval: float = 5.0,
    chunk_label: str = "",
) -> None:
    """Restart the Valhalla Docker container and block until the service responds."""
    url = (base_url or config.VALHALLA_BASE_URL).rstrip("/")
    msg = f"Restarting Docker container '{container_name}'{chunk_label} …"
    LOG.info(msg)
    print(msg, flush=True)
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip() or f"exit code {result.returncode}"
            LOG.warning("docker restart failed: %s", err)
            print(f"WARNING: docker restart failed: {err}", flush=True)
            print("  Run 'docker ps' to see the exact container name (e.g. valhalla_valhalla_1).", flush=True)
            return
    except FileNotFoundError as e:
        LOG.warning("Docker not found in PATH: %s", e)
        print(f"WARNING: Docker not found. {e}", flush=True)
        return
    except subprocess.TimeoutExpired:
        LOG.warning("docker restart timed out after 120s")
        print("WARNING: docker restart timed out.", flush=True)
        return
    status_url = f"{url}/status"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            r = requests.get(status_url, timeout=5)
            if r.status_code == 200:
                LOG.info("Valhalla is back up at %s", url)
                print("Valhalla back up, starting next chunk.", flush=True)
                return
        except requests.RequestException:
            pass
    LOG.warning("Valhalla did not respond within %ds; proceeding with next chunk anyway.", timeout_seconds)
    print(f"WARNING: Valhalla did not respond within {timeout_seconds}s.", flush=True)


def _merge_chunk_outputs(chunk_paths: list[Path], final_path: Path) -> tuple[int, int]:
    """Merge chunk parquet outputs into a single final matrix file."""
    import pyarrow.parquet as pq

    if final_path.exists():
        final_path.unlink()

    writer = None
    total_rows = 0
    total_inf = 0
    try:
        for chunk_path in chunk_paths:
            chunk_df = pd.read_parquet(chunk_path)
            total_rows += len(chunk_df)
            total_inf += int(np.isinf(chunk_df["duration_min"].to_numpy(dtype=float, na_value=np.nan)).sum())

            table = pq.read_table(chunk_path)
            if writer is None:
                writer = pq.ParquetWriter(final_path, table.schema)
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()

    return total_rows, total_inf


def merge_county_matrix_chunks(
    matrix_path: Path | None = None,
) -> Path:
    """Merge existing chunk parquets into the final county matrix. Use after all chunks are done (e.g. manual runs)."""
    profile = get_profile("usa_low_detail_county")
    path = matrix_path or (config.TABLES_DIR / f"{profile.output_prefix}_county_travel_time_matrix.parquet")
    chunk_dir = path.parent / f"{path.stem}_chunks"
    if not chunk_dir.is_dir():
        raise FileNotFoundError(f"Chunk directory not found: {chunk_dir}")
    pattern = f"{path.stem}_chunk_*.parquet"
    chunk_paths = sorted(chunk_dir.glob(pattern), key=lambda p: p.name)
    if not chunk_paths:
        raise FileNotFoundError(f"No chunk files matching {pattern} in {chunk_dir}")
    n_total, n_inf = _merge_chunk_outputs(chunk_paths, path)
    LOG.info("Merged %d chunks -> %s (rows=%d, inf=%d).", len(chunk_paths), path, n_total, n_inf)
    print(f"Merged {len(chunk_paths)} chunks -> {path}  (rows={n_total:,}, inf={n_inf:,})", flush=True)
    return path


def run_county_valhalla_matrix(
    out_path: Path | None = None,
    pop_col: str = "total_pop",
    chunk_size: int = DEFAULT_COUNTY_CHUNK_SIZE,
    force_rebuild_origins: bool = False,
    restart_container_after_chunk: str | None = None,
    only_chunk: int | None = None,
) -> Path:
    """Compute a county-centroid to hospital travel-time matrix using Valhalla."""
    profile = get_profile("usa_low_detail_county")
    validate_county_only_profile(profile)

    LOG.info("Preparing county origins and hospital destinations for low-detail USA routing …")
    facilities = build_facilities()
    counties = build_county_origins(pop_col=pop_col, force_rebuild=force_rebuild_origins)

    if "AHA_ID" not in facilities.columns:
        raise ValueError("Expected column 'AHA_ID' in facilities; cannot build destinations.")

    origins = counties.rename(columns={"county_fips": "origin_id"})
    matrix_path = out_path or (config.TABLES_DIR / f"{profile.output_prefix}_county_travel_time_matrix.parquet")
    chunk_dir = matrix_path.parent / f"{matrix_path.stem}_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    LOG.info(
        "Computing county-centroid travel-time matrix with Valhalla: %d counties × %d facilities in chunks of %d origins.",
        len(origins),
        len(facilities),
        chunk_size,
    )

    n_chunks = (len(origins) + chunk_size - 1) // chunk_size
    if only_chunk is not None:
        if not (1 <= only_chunk <= n_chunks):
            raise ValueError(f"--chunk must be between 1 and {n_chunks}, got {only_chunk}")
        LOG.info("Manual chunk mode: running only chunk %d/%d (no auto-restart, no merge).", only_chunk, n_chunks)
        print(f"Manual chunk mode: running only chunk {only_chunk}/{n_chunks}. Restart Docker yourself between runs.", flush=True)
        container_to_restart = None
    else:
        container_to_restart = restart_container_after_chunk or config.VALHALLA_CONTAINER_NAME
        if container_to_restart is not None:
            container_to_restart = str(container_to_restart).strip() or None
        if container_to_restart:
            LOG.info("Docker restart after each chunk enabled (container: %s)", container_to_restart)
            print(f"Docker restart after each chunk: container '{container_to_restart}'", flush=True)
        else:
            LOG.info("Docker restart after each chunk disabled (set VALHALLA_CONTAINER_NAME or --restart-container to enable)")

    chunk_paths: list[Path] = []
    for chunk_idx, chunk_origins in _iter_origin_chunks(origins, chunk_size):
        if only_chunk is not None and chunk_idx != only_chunk:
            continue
        chunk_path = chunk_dir / f"{matrix_path.stem}_chunk_{chunk_idx:03d}.parquet"
        LOG.info(
            "Routing chunk %d/%d: %d county origins -> %s",
            chunk_idx,
            n_chunks,
            len(chunk_origins),
            chunk_path,
        )
        compute_travel_time_matrix(
            origins=chunk_origins,
            destinations=facilities,
            origin_id_col="origin_id",
            dest_id_col="AHA_ID",
            out_path=chunk_path,
            routing_engine="valhalla",
            batch_size=8,
            max_workers=2,
            max_haversine_km=150.0,
            min_k=3,
            return_df=False,
        )
        chunk_paths.append(chunk_path)
        if container_to_restart and chunk_idx < n_chunks:
            _restart_valhalla_and_wait(
                container_to_restart,
                chunk_label=f" after chunk {chunk_idx}/{n_chunks}",
            )

    if only_chunk is not None:
        print(f"Chunk {only_chunk}/{n_chunks} done: {chunk_paths[0]}", flush=True)
        if only_chunk < n_chunks:
            print(f"Restart Docker, then run: --chunk {only_chunk + 1}", flush=True)
        else:
            print("All chunks done. Run with --merge-only to build the final matrix.", flush=True)
        return chunk_paths[0]

    n_total, n_inf = _merge_chunk_outputs(chunk_paths, matrix_path)
    LOG.info(
        "County-centroid matrix completed. Saved to %s (rows=%d, inf=%d, chunks=%d).",
        matrix_path,
        n_total,
        n_inf,
        len(chunk_paths),
    )
    print(f"County matrix rows: {n_total:,}  |  inf durations: {n_inf:,}  |  chunks: {len(chunk_paths):,}")
    return matrix_path


def main() -> None:
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="County-centroid to hospital Valhalla matrix (USA low-detail).")
    p.add_argument(
        "--restart-container",
        metavar="NAME",
        default=None,
        help="Docker container name to restart after each chunk (e.g. valhalla-hires). Overrides VALHALLA_CONTAINER_NAME.",
    )
    p.add_argument(
        "--chunk",
        type=int,
        metavar="N",
        default=None,
        help="Run only chunk N (1-based). No auto-restart, no merge. Restart Docker yourself, then run --chunk N+1.",
    )
    p.add_argument(
        "--merge-only",
        action="store_true",
        help="Only merge existing chunk parquets into the final matrix. Use after all chunks are done (e.g. manual runs).",
    )
    args = p.parse_args()
    if args.merge_only:
        path = merge_county_matrix_chunks()
        print(f"Merged matrix saved to: {path}")
        return
    path = run_county_valhalla_matrix(
        restart_container_after_chunk=args.restart_container,
        only_chunk=args.chunk,
    )
    if args.chunk is None:
        print(f"USA low-detail county-centroid Valhalla matrix saved to: {path}")


if __name__ == "__main__":
    main()

