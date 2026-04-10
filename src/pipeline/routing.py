"""
Travel-time matrix computation via Valhalla (/sources_to_targets) or OSRM (/table/v1/driving).
Stores tract-to-facility duration matrix; handles batching, parallelism, and Haversine prefiltering.
Active engine is controlled by config.ROUTING_ENGINE (default: "valhalla").
"""
from __future__ import annotations

import logging
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config

LOG = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 50
DEFAULT_MAX_WORKERS = 6
DEFAULT_PREFILTER_ORIGIN_BLOCK_SIZE = 2_048
DEFAULT_MAX_PENDING_TASKS_FACTOR = 2
# Performance guards: warn when full matrix or batch count may cause long runs / OOM
PREFILTER_WARN_FULL_PAIRS = 1_000_000
LARGE_BATCH_WARN = 50_000
INF_FALLBACK_WARN_COUNT = 100
OUTPUT_COLUMNS = [
    "origin_id",
    "destination_id",
    "duration_min",
    "valhalla_status_code",
    "valhalla_error",
]


def validate_routing_inputs(
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    origin_id_col: str,
    dest_id_col: str,
) -> None:
    """Validate that routing inputs have the required ID and coordinate columns."""
    missing_orig = {origin_id_col, "centroid_lat", "centroid_lon"} - set(origins.columns)
    if missing_orig:
        raise ValueError(f"Origins missing required columns for routing: {sorted(missing_orig)}")
    missing_dest = {dest_id_col, "latitude", "longitude"} - set(destinations.columns)
    if missing_dest:
        raise ValueError(f"Destinations missing required columns for routing: {sorted(missing_dest)}")


# ---------------------------------------------------------------------------
# Haversine prefilter — eliminate impossible pairs before touching OSRM
# ---------------------------------------------------------------------------

def _haversine_matrix_km(
    lat1: np.ndarray, lon1: np.ndarray,
    lat2: np.ndarray, lon2: np.ndarray,
) -> np.ndarray:
    """Vectorized Haversine: (N,) origins x (M,) destinations -> (N, M) km."""
    R = 6_371.0
    rlat1 = np.radians(lat1)[:, None]
    rlon1 = np.radians(lon1)[:, None]
    rlat2 = np.radians(lat2)[None, :]
    rlon2 = np.radians(lon2)[None, :]
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = np.sin(dlat / 2) ** 2 + np.cos(rlat1) * np.cos(rlat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def prefilter_candidates(
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    max_haversine_km: float | None = None,
    min_k: int | None = None,
    origin_block_size: int | None = None,
) -> dict[int, np.ndarray]:
    """For each origin row-index, return destination row-indices worth routing.

    Keeps every destination within *max_haversine_km* (default 300 km).
    If fewer than *min_k* (default 30) fall within the radius, the closest
    *min_k* are kept so even very remote tracts get candidates.

    At highway speed (~110 km/h), 300 km Haversine ≈ 400+ km road ≈ 3.5+ h
    of driving — well beyond the 90-min step-decay cutoff (g(t)=0).
    So every pair that *matters* for BEI / access times is included.
    """
    max_km = max_haversine_km if max_haversine_km is not None else config.ROUTING_MAX_HAVERSINE_KM
    k = min_k if min_k is not None else config.ROUTING_MIN_K

    candidates: dict[int, np.ndarray] = {}
    block_size = origin_block_size or DEFAULT_PREFILTER_ORIGIN_BLOCK_SIZE

    origin_lat = origins["centroid_lat"].values.astype(float)
    origin_lon = origins["centroid_lon"].values.astype(float)
    dest_lat = destinations["latitude"].values.astype(float)
    dest_lon = destinations["longitude"].values.astype(float)

    for start in range(0, len(origins), block_size):
        stop = min(start + block_size, len(origins))
        dist_block = _haversine_matrix_km(
            origin_lat[start:stop],
            origin_lon[start:stop],
            dest_lat,
            dest_lon,
        )
        for offset, dist_row in enumerate(dist_block):
            i = start + offset
            within = np.flatnonzero(dist_row <= max_km)
            if len(within) >= k:
                candidates[i] = within
            else:
                candidates[i] = np.argsort(dist_row)[:k]
    return candidates


# ---------------------------------------------------------------------------
# Single routing request (OSRM or Valhalla)
# ---------------------------------------------------------------------------

def _run_one_batch_osrm(
    o_indices: np.ndarray,
    d_indices: np.ndarray,
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    url: str,
    origin_id_col: str,
    dest_id_col: str,
) -> list[dict]:
    """Execute one OSRM table request for specific origin/destination indices."""
    o_batch = origins.iloc[o_indices]
    d_batch = destinations.iloc[d_indices]
    n_o = len(o_batch)
    n_d = len(d_batch)
    coords = []
    for _, r in o_batch.iterrows():
        coords.append(f"{r['centroid_lon']},{r['centroid_lat']}")
    for _, r in d_batch.iterrows():
        coords.append(f"{r['longitude']},{r['latitude']}")
    coord_str = ";".join(coords)

    src_idx = ";".join(str(i) for i in range(n_o))
    dst_idx = ";".join(str(i) for i in range(n_o, n_o + n_d))

    rows: list[dict] = []
    try:
        r = requests.get(
            url,
            params={
                "coordinates": coord_str,
                "sources": src_idx,
                "destinations": dst_idx,
                "annotations": "duration",
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        durations = data.get("durations") or []
        for i, dur_row in enumerate(durations):
            o_id = o_batch.iloc[i][origin_id_col]
            for j, dur in enumerate(dur_row):
                d_id = d_batch.iloc[j][dest_id_col]
                rows.append({
                    "origin_id": o_id,
                    "destination_id": d_id,
                    "duration_min": (dur / 60.0) if dur is not None else float("inf"),
                })
    except Exception as e:
        LOG.warning("OSRM batch failed (o=%s, d=%s): %s", len(o_indices), len(d_indices), e)
    return rows


def _run_one_batch_valhalla(
    o_indices: np.ndarray,
    d_indices: np.ndarray,
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    url: str,
    origin_id_col: str,
    dest_id_col: str,
    session: "requests.Session | None" = None,
) -> list[dict]:
    """Execute one Valhalla matrix request for specific origin/destination indices."""
    _session = session or requests.Session()

    def _response_excerpt(exc: requests.HTTPError) -> str:
        response = exc.response
        if response is None:
            return ""
        text = (response.text or "").strip().replace("\n", " ")
        return text[:300]

    def _matrix_rows(o_idx: np.ndarray, d_idx: np.ndarray, matrix: list[list[dict | None]]) -> list[dict]:
        o_batch = origins.iloc[o_idx]
        d_batch = destinations.iloc[d_idx]
        rows: list[dict] = []
        for i, dur_row in enumerate(matrix):
            o_id = o_batch.iloc[i][origin_id_col]
            for j, cell in enumerate(dur_row):
                d_id = d_batch.iloc[j][dest_id_col]
                sec = cell.get("time") if isinstance(cell, dict) else None
                rows.append({
                    "origin_id": o_id,
                    "destination_id": d_id,
                    "duration_min": (sec / 60.0) if sec is not None else float("inf"),
                })
        return rows

    def _inf_rows(
        o_idx: np.ndarray,
        d_idx: np.ndarray,
        error_text: str | None = None,
        status_code: int | None = None,
    ) -> list[dict]:
        o_batch = origins.iloc[o_idx]
        d_batch = destinations.iloc[d_idx]
        return [{
            "origin_id": o_batch.iloc[0][origin_id_col],
            "destination_id": d_batch.iloc[0][dest_id_col],
            "duration_min": float("inf"),
            "valhalla_status_code": status_code,
            "valhalla_error": error_text,
        }]

    def _request_with_retry(o_idx: np.ndarray, d_idx: np.ndarray) -> list[dict]:
        o_batch = origins.iloc[o_idx]
        d_batch = destinations.iloc[d_idx]
        payload = {
            "sources": [
                {"lat": float(r["centroid_lat"]), "lon": float(r["centroid_lon"])}
                for _, r in o_batch.iterrows()
            ],
            "targets": [
                {"lat": float(r["latitude"]), "lon": float(r["longitude"])}
                for _, r in d_batch.iterrows()
            ],
            "costing": "auto",
            "units": "kilometers",
        }

        try:
            r = _session.post(url, json=payload, timeout=config.VALHALLA_REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            return _matrix_rows(o_idx, d_idx, data.get("sources_to_targets") or [])
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 400:
                if len(o_idx) > 1:
                    mid = max(1, len(o_idx) // 2)
                    LOG.warning(
                        "Valhalla 400 for batch (o=%s, d=%s); splitting origins into %s and %s.",
                        len(o_idx), len(d_idx), mid, len(o_idx) - mid,
                    )
                    return (
                        _request_with_retry(o_idx[:mid], d_idx)
                        + _request_with_retry(o_idx[mid:], d_idx)
                    )
                if len(d_idx) > 1:
                    mid = max(1, len(d_idx) // 2)
                    LOG.warning(
                        "Valhalla 400 for batch (o=%s, d=%s); splitting destinations into %s and %s.",
                        len(o_idx), len(d_idx), mid, len(d_idx) - mid,
                    )
                    return (
                        _request_with_retry(o_idx, d_idx[:mid])
                        + _request_with_retry(o_idx, d_idx[mid:])
                    )

                LOG.warning(
                    "Valhalla rejected single pair (origin=%s, dest=%s). Fallback: recording inf duration. Response: %s",
                    o_batch.iloc[0][origin_id_col],
                    d_batch.iloc[0][dest_id_col],
                    _response_excerpt(exc),
                )
                return _inf_rows(
                    o_idx,
                    d_idx,
                    error_text=_response_excerpt(exc),
                    status_code=status_code,
                )

            LOG.warning(
                "Valhalla batch failed (o=%s, d=%s, status=%s): %s",
                len(o_idx), len(d_idx), status_code, exc,
            )
            return []
        except Exception as exc:
            LOG.warning("Valhalla batch failed (o=%s, d=%s): %s", len(o_idx), len(d_idx), exc)
            return []

    return _request_with_retry(np.asarray(o_indices), np.asarray(d_indices))


def _run_one_batch(
    o_indices: np.ndarray,
    d_indices: np.ndarray,
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    url: str,
    origin_id_col: str,
    dest_id_col: str,
    routing_engine: str,
    session: "requests.Session | None" = None,
) -> list[dict]:
    """Dispatch a batch request to configured routing engine."""
    if routing_engine == "osrm":
        return _run_one_batch_osrm(
            o_indices, d_indices, origins, destinations, url, origin_id_col, dest_id_col
        )
    if routing_engine == "valhalla":
        return _run_one_batch_valhalla(
            o_indices, d_indices, origins, destinations, url, origin_id_col, dest_id_col,
            session=session,
        )
    raise ValueError(f"Unsupported routing engine: {routing_engine}")


# ---------------------------------------------------------------------------
# Build tasks from prefiltered candidates
# ---------------------------------------------------------------------------

def _build_tasks(
    candidates: dict[int, np.ndarray],
    n_origins: int,
    batch_size: int,
    sort_by_lon: np.ndarray | None = None,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Group origins into batches, compute union of candidate destinations
    for each batch, and produce (origin_indices, dest_indices) task tuples.
    Origins are sorted by longitude so nearby tracts share destinations."""
    if sort_by_lon is not None:
        order = np.argsort(sort_by_lon)
    else:
        order = np.arange(n_origins)

    tasks: list[tuple[np.ndarray, np.ndarray]] = []
    for start in range(0, len(order), batch_size):
        o_indices = order[start : start + batch_size]
        d_union = np.unique(np.concatenate([candidates[i] for i in o_indices]))
        # Sub-batch destinations if union exceeds batch_size
        for d_start in range(0, len(d_union), batch_size):
            d_sub = d_union[d_start : d_start + batch_size]
            tasks.append((o_indices, d_sub))
    return tasks


def _build_full_tasks(
    n_origins: int, n_destinations: int, batch_size: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Full (unfiltered) Cartesian batching."""
    tasks: list[tuple[np.ndarray, np.ndarray]] = []
    for o_start in range(0, n_origins, batch_size):
        o_indices = np.arange(o_start, min(o_start + batch_size, n_origins))
        for d_start in range(0, n_destinations, batch_size):
            d_indices = np.arange(d_start, min(d_start + batch_size, n_destinations))
            tasks.append((o_indices, d_indices))
    return tasks


def _build_valhalla_tasks(
    candidates: dict[int, np.ndarray],
    n_origins: int,
    batch_size: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create Valhalla-safe tasks with one origin per request."""
    tasks: list[tuple[np.ndarray, np.ndarray]] = []
    for i in range(n_origins):
        d_candidates = candidates[i]
        for d_start in range(0, len(d_candidates), batch_size):
            d_sub = d_candidates[d_start : d_start + batch_size]
            tasks.append((np.array([i]), d_sub))
    return tasks


def _iter_valhalla_tasks(
    candidates: dict[int, np.ndarray],
    n_origins: int,
    batch_size: int,
):
    """Yield Valhalla-safe tasks lazily with one origin per request."""
    for i in range(n_origins):
        d_candidates = candidates[i]
        for d_start in range(0, len(d_candidates), batch_size):
            d_sub = d_candidates[d_start : d_start + batch_size]
            yield np.array([i]), d_sub


def _count_valhalla_tasks(
    candidates: dict[int, np.ndarray],
    batch_size: int,
) -> int:
    """Count how many one-origin Valhalla requests the candidate map implies."""
    return sum((len(d_idx) + batch_size - 1) // batch_size for d_idx in candidates.values())


def _build_full_valhalla_tasks(
    n_origins: int,
    n_destinations: int,
    batch_size: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Full Valhalla batching with one origin per request."""
    tasks: list[tuple[np.ndarray, np.ndarray]] = []
    for i in range(n_origins):
        o_indices = np.array([i])
        for d_start in range(0, n_destinations, batch_size):
            d_indices = np.arange(d_start, min(d_start + batch_size, n_destinations))
            tasks.append((o_indices, d_indices))
    return tasks


def _iter_full_valhalla_tasks(
    n_origins: int,
    n_destinations: int,
    batch_size: int,
):
    """Yield full Valhalla tasks lazily with one origin per request."""
    for i in range(n_origins):
        o_indices = np.array([i])
        for d_start in range(0, n_destinations, batch_size):
            d_indices = np.arange(d_start, min(d_start + batch_size, n_destinations))
            yield o_indices, d_indices


def _count_full_valhalla_tasks(
    n_origins: int,
    n_destinations: int,
    batch_size: int,
) -> int:
    """Count full one-origin Valhalla requests without materializing them."""
    if n_destinations == 0:
        return 0
    return n_origins * ((n_destinations + batch_size - 1) // batch_size)


def _batch_rows_to_frame(batch_rows: list[dict]) -> pd.DataFrame:
    """Normalize per-batch rows to a consistent schema for streaming writes."""
    if not batch_rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    batch_df = pd.DataFrame.from_records(batch_rows)
    for column in OUTPUT_COLUMNS:
        if column not in batch_df.columns:
            batch_df[column] = pd.NA

    batch_df = batch_df[OUTPUT_COLUMNS].copy()
    batch_df["origin_id"] = batch_df["origin_id"].astype("string")
    batch_df["destination_id"] = batch_df["destination_id"].astype("string")
    batch_df["duration_min"] = pd.to_numeric(batch_df["duration_min"], errors="coerce")
    batch_df["valhalla_status_code"] = pd.to_numeric(
        batch_df["valhalla_status_code"], errors="coerce"
    ).astype("Int64")
    batch_df["valhalla_error"] = batch_df["valhalla_error"].astype("string")
    return batch_df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_travel_time_matrix(path: Path | None = None) -> pd.DataFrame:
    """Load the travel-time matrix from a previously saved parquet file.

    Use this for future retrieval after the matrix has been computed and saved.
    Default path is config.TRAVEL_TIME_MATRIX_PATH.
    """
    load_path = path if path is not None else config.TRAVEL_TIME_MATRIX_PATH
    if not load_path.exists():
        raise FileNotFoundError(
            f"Travel time matrix not found at {load_path}. "
            "Run compute_travel_time_matrix() first (with OSRM server running)."
        )
    return pd.read_parquet(load_path)


def get_travel_time_matrix(
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    path: Path | None = None,
    force_recompute: bool = False,
    **compute_kwargs: object,
) -> pd.DataFrame:
    """Load cached travel-time matrix if available, otherwise compute and save it.

    Use path (default config.TRAVEL_TIME_MATRIX_PATH) for both load and save.
    Set force_recompute=True to ignore cache and recompute.
    """
    load_path = path if path is not None else config.TRAVEL_TIME_MATRIX_PATH
    if not force_recompute and load_path.exists():
        LOG.info("Loading cached travel time matrix from %s", load_path)
        return load_travel_time_matrix(path=load_path)
    return compute_travel_time_matrix(
        origins, destinations, out_path=load_path, **compute_kwargs
    )


def compute_travel_time_matrix(
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    origin_id_col: str = "tract_geoid",
    dest_id_col: str = "AHA_ID",
    base_url: str | None = None,
    out_path: Path | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_workers: int | None = None,
    prefilter: bool = True,
    max_haversine_km: float | None = None,
    min_k: int | None = None,
    routing_engine: str | None = None,
    return_df: bool = True,
) -> pd.DataFrame:
    """Query routing matrix service; optionally return the saved matrix as a DataFrame.

    When *prefilter=True* (default), a Haversine pre-screen eliminates distant
    pairs before any routing call. This typically reduces requests from ~22 000
    to ~2 000 (≈10× fewer) without affecting results: facilities beyond 300 km
    air-line are guaranteed to be >90 min driving, and the step-decay g(t)=0.
    """
    if max_workers is None:
        max_workers = config.OSRM_MAX_WORKERS
    engine = (routing_engine or config.ROUTING_ENGINE).lower()
    if engine not in {"osrm", "valhalla"}:
        raise ValueError(f"Unsupported routing engine: {engine}")

    # Performance guards: warn when prefilter is off for large matrices or batch count is high
    full_pairs = len(origins) * len(destinations)
    if not prefilter and full_pairs > PREFILTER_WARN_FULL_PAIRS:
        LOG.warning(
            "Prefilter disabled with %s origin-destination pairs; run may be slow or OOM. Consider prefilter=True.",
            f"{full_pairs:,}",
        )

    if engine == "osrm":
        base_url = base_url or config.OSRM_BASE_URL
        url = f"{base_url}{config.OSRM_TABLE_SERVICE}"
    else:
        base_url = base_url or config.VALHALLA_BASE_URL
        url = f"{base_url}{config.VALHALLA_MATRIX_SERVICE}"

    engine_label = engine.upper()

    from tqdm.auto import tqdm

    # --- Prefilter ---
    if prefilter:
        LOG.info("Haversine prefilter: computing air-line distances for %d origins × %d destinations …",
                 len(origins), len(destinations))
        candidates = prefilter_candidates(origins, destinations, max_haversine_km, min_k)
        total_pairs = sum(len(v) for v in candidates.values())
        full_pairs = len(origins) * len(destinations)
        pct = total_pairs / full_pairs * 100
        LOG.info("Prefilter kept %s / %s pairs (%.1f%%). Building tasks …", f"{total_pairs:,}", f"{full_pairs:,}", pct)
        tqdm.write(
            f"Haversine prefilter: {total_pairs:,} / {full_pairs:,} pairs kept "
            f"({pct:.1f}%) — {full_pairs - total_pairs:,} pairs skipped"
        )
        if engine == "valhalla":
            total_batches = _count_valhalla_tasks(candidates, batch_size)
            task_iter = _iter_valhalla_tasks(candidates, len(origins), batch_size)
        else:
            tasks = _build_tasks(
                candidates, len(origins), batch_size,
                sort_by_lon=origins["centroid_lon"].values.astype(float),
            )
            total_batches = len(tasks)
            task_iter = iter(tasks)
    else:
        if engine == "valhalla":
            total_batches = _count_full_valhalla_tasks(len(origins), len(destinations), batch_size)
            task_iter = _iter_full_valhalla_tasks(len(origins), len(destinations), batch_size)
        else:
            tasks = _build_full_tasks(len(origins), len(destinations), batch_size)
            total_batches = len(tasks)
            task_iter = iter(tasks)

    if total_batches > LARGE_BATCH_WARN:
        LOG.warning(
            "Large number of routing batches (%s); expect long runtime. Consider prefilter=True or smaller geography.",
            f"{total_batches:,}",
        )
    tqdm.write(f"{engine_label} requests to send: {total_batches:,}")

    # --- Execute ---
    import requests as _requests
    import pyarrow as pa
    import pyarrow.parquet as pq

    session = _requests.Session()
    adapter = _requests.adapters.HTTPAdapter(
        pool_connections=max_workers, pool_maxsize=max_workers, max_retries=1,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    save_path = out_path if out_path is not None else config.TRAVEL_TIME_MATRIX_PATH
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        try:
            save_path.unlink()
        except PermissionError as exc:
            LOG.warning(
                "Existing matrix file %s is locked by another process; "
                "close any viewer (e.g. Excel) and rerun. Original error: %s",
                save_path,
                exc,
            )
            raise

    output_schema = pa.schema([
        ("origin_id", pa.string()),
        ("destination_id", pa.string()),
        ("duration_min", pa.float64()),
        ("valhalla_status_code", pa.int64()),
        ("valhalla_error", pa.string()),
    ])
    parquet_writer = None
    total_rows_written = 0

    inf_csv_path = save_path.with_name(f"{save_path.stem}_inf.csv")
    if inf_csv_path.exists():
        inf_csv_path.unlink()
    wrote_inf_header = False
    origin_coords = origins[[origin_id_col, "centroid_lat", "centroid_lon"]].drop_duplicates().rename(
        columns={
            origin_id_col: "origin_id",
            "centroid_lat": "origin_lat",
            "centroid_lon": "origin_lon",
        }
    )
    origin_coords["origin_id"] = origin_coords["origin_id"].astype("string")
    dest_coords = destinations[[dest_id_col, "latitude", "longitude"]].drop_duplicates().rename(
        columns={
            dest_id_col: "destination_id",
            "latitude": "destination_lat",
            "longitude": "destination_lon",
        }
    )
    dest_coords["destination_id"] = dest_coords["destination_id"].astype("string")

    def _persist_batch(batch_rows: list[dict]) -> None:
        nonlocal parquet_writer, total_rows_written, wrote_inf_header

        batch_df = _batch_rows_to_frame(batch_rows)
        if batch_df.empty:
            return

        table = pa.Table.from_pandas(batch_df, schema=output_schema, preserve_index=False)
        if parquet_writer is None:
            parquet_writer = pq.ParquetWriter(save_path, output_schema)
        parquet_writer.write_table(table)
        total_rows_written += len(batch_df)

        inf_mask = np.isinf(batch_df["duration_min"].to_numpy(dtype=float, na_value=np.nan))
        if inf_mask.any():
            inf_df = batch_df.loc[inf_mask].copy()
            inf_df = inf_df.merge(origin_coords, on="origin_id", how="left")
            inf_df = inf_df.merge(dest_coords, on="destination_id", how="left")
            inf_df.to_csv(
                inf_csv_path,
                mode="a",
                header=not wrote_inf_header,
                index=False,
            )
            wrote_inf_header = True

    try:
        if max_workers <= 1:
            with tqdm(total=total_batches, desc=f"{engine_label} routing", unit="batch", leave=True) as pbar:
                for o_idx, d_idx in task_iter:
                    pbar.set_postfix_str(f"{len(o_idx)} origins × {len(d_idx)} dests")
                    batch_rows = _run_one_batch(
                        o_idx, d_idx, origins, destinations, url, origin_id_col, dest_id_col, engine,
                        session=session,
                    )
                    _persist_batch(batch_rows)
                    pbar.update(1)
        else:
            max_pending = max(max_workers, max_workers * DEFAULT_MAX_PENDING_TASKS_FACTOR)
            with tqdm(total=total_batches, desc=f"{engine_label} routing", unit="batch", leave=True) as pbar:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    pending: dict = {}

                    def _submit_next_task() -> bool:
                        try:
                            o_idx, d_idx = next(task_iter)
                        except StopIteration:
                            return False
                        future = executor.submit(
                            _run_one_batch,
                            o_idx,
                            d_idx,
                            origins,
                            destinations,
                            url,
                            origin_id_col,
                            dest_id_col,
                            engine,
                            session,
                        )
                        pending[future] = (o_idx, d_idx)
                        return True

                    for _ in range(max_pending):
                        if not _submit_next_task():
                            break

                    while pending:
                        done, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
                        for future in done:
                            o_idx, d_idx = pending.pop(future)
                            batch_rows = future.result()
                            _persist_batch(batch_rows)
                            pbar.update(1)
                            pbar.set_postfix_str(f"{len(o_idx)} origins × {len(d_idx)} dests")
                            while len(pending) < max_pending and _submit_next_task():
                                pass
    finally:
        session.close()
        if parquet_writer is not None:
            parquet_writer.close()

    if parquet_writer is None:
        _batch_rows_to_frame([]).to_parquet(save_path, index=False)

    if wrote_inf_header:
        inf_count = sum(len(chunk) for chunk in pd.read_csv(inf_csv_path, chunksize=100_000))
        LOG.info(
            "Detected %d inf-duration rows; wrote diagnostics CSV to %s",
            inf_count,
            inf_csv_path,
        )
        if inf_count >= INF_FALLBACK_WARN_COUNT:
            LOG.warning(
                "Many pairs fell back to inf duration (%d). Check Valhalla connectivity and origin/destination coordinates.",
                inf_count,
            )

    LOG.info("Travel time matrix saved to %s (%d rows)", save_path, total_rows_written)
    if return_df:
        return pd.read_parquet(save_path)
    return pd.DataFrame(columns=OUTPUT_COLUMNS)
