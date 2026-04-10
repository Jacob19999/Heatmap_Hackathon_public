# Computation Requirements (Full Pipeline, All States)

Rough requirements for running the full BEI pipeline with **all US census tracts** and **all NIRD facilities**, with OSRM providing driving-time matrices.

## Scale (national)


| Item                                | Approximate count    | Source                  |
| ----------------------------------- | -------------------- | ----------------------- |
| Census tracts (origins)             | ~84,000              | TIGER tract count       |
| NIRD facilities (destinations)      | ~635                 | NIRD burn + trauma      |
| All tract-facility pairs            | ~53 million          | 84,000 x 635            |
| **Pairs after Haversine prefilter** | **~1.5-2.5 million** | ~20-30 candidates/tract |


## Haversine prefilter (default ON)

Before any OSRM call, we compute air-line (Haversine) distance for all 53M pairs (instant, numpy vectorized). Then for each tract we keep only:

- Facilities within **300 km** Haversine, **or**
- The **closest 30** facilities (safety net for very remote tracts).

**Why this is safe** -- zero loss of accuracy:


| Consumer                             | What it needs                                 | Why prefilter is exact                                                                                                                                          |
| ------------------------------------ | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **access.py** (T_dir, T_stab, T_sys) | `min()` over facilities                       | Haversine <= driving distance. If a facility is the true driving-nearest, it's always among the Haversine-nearest. The min-K=30 safety net guarantees inclusion. |
| **bei_components.py** (E2SFCA)       | `g(t_ij)` step-decay, **g(t)=0 for t>90 min** | 300 km Haversine ~ 400+ km road ~ 3.5+ h driving. Any pair beyond 300 km air-line is guaranteed >90 min driving -> `g(t)=0` -> contributes nothing.               |


**Typical reduction**: ~53M pairs -> ~1.5-2.5M pairs (**~20-30x fewer**).

## OSRM routing

- **Batch size**: up to 50 origins + 50 destinations per request (OSRM limit ~100 coordinates).
- Origins are **sorted by longitude** so nearby tracts share candidate destinations; the union of candidates per batch is small.


| Scenario                     | Requests         | Time (parallel, 6 workers) |
| ---------------------------- | ---------------- | -------------------------- |
| **Without** prefilter        | ~21,840          | ~2-5 hours                 |
| **With** prefilter (default) | **~1,700-2,500** | **~15-45 minutes**         |


To disable prefiltering (full Cartesian): `compute_travel_time_matrix(..., prefilter=False)`.

## Disk


| Resource                                                | Size (approx) |
| ------------------------------------------------------- | ------------- |
| US OSM extract (`us-latest.osm.pbf`)                    | ~11 GB        |
| OSRM processed data (after extract/partition/customize) | ~5-15 GB      |
| TIGER tract shapefiles (all states)                     | ~2-4 GB       |
| ACS, RUCA, outputs (parquet/geojson)                    | ~1-2 GB       |
| **Total**                                               | **~20-35 GB** |


## Memory (RAM)

**OSRM extract is the bottleneck.** `osrm-extract` builds per-thread in-memory
data structures for ways/nodes, so peak RAM scales linearly with thread count:

| Threads | Approx peak RAM (full US) | Time          |
| ------- | ------------------------- | ------------- |
| 24      | 20-30+ GB                 | ~15 min       |
| 4       | 14-18 GB                  | ~30 min       |
| 2       | 10-12 GB                  | ~45-60 min    |
| 1       | 8-10 GB                   | ~90-120 min   |

Other stages:
- **TIGER load**: 2-8 GB (geopandas).
- **Travel-time matrix**: ~1.5-2.5M rows (with prefilter) -> **~100-200 MB** in pandas.
- **OSRM server** (`osrm-routed`): ~2-4 GB for the US graph in memory.

### WSL2 `.wslconfig` recommendation

With 16 GB physical RAM, `osrm-extract` will spill beyond available memory.
Set a **large swap** (disk-backed, free except disk space) so it spills instead of crashing:

```ini
[wsl2]
memory=16GB
processors=4
swap=32GB
```

Save as `%UserProfile%\.wslconfig`, then `wsl --shutdown` and reopen Docker Desktop.
The setup script now defaults to 2 threads. Use `-Threads 1` if still OOM.

**Suggested**: **16 GB RAM + 32 GB swap** recommended; **8 GB** may work with regional extracts only.

## CPU

- **OSRM extract/partition/customize**: Multi-threaded; benefits from **4+ cores** (30-90+ min for full US at 2 threads).
- **Haversine prefilter**: ~53M distances via numpy -- **<5 seconds** on any modern CPU.
- **Pipeline (ingest, geocode, augment, access)**: Mostly I/O and single-threaded; 2-4 cores sufficient.
- **Routing step**: Network-bound (HTTP to local OSRM); client CPU is not the bottleneck.

## Summary


| Requirement       | Full US (with prefilter)                |
| ----------------- | --------------------------------------- |
| Disk              | ~20 GB free                             |
| RAM               | 16 GB + 32 GB swap recommended          |
| CPU               | 4+ cores for OSRM prep; 2+ for pipeline |
| OSRM extract      | 2 threads (default), 45-60 min          |
| OSRM API calls    | ~1,700-2,500                            |
| Routing wall time | **~15-45 min** (parallel, 6 workers)    |


## Config

Tunables in `src/pipeline/config.py`:


| Constant                   | Default | Purpose                                    |
| -------------------------- | ------- | ------------------------------------------ |
| `ROUTING_MAX_HAVERSINE_KM` | 300     | Air-line cutoff for candidate destinations |
| `ROUTING_MIN_K`            | 30      | Minimum candidates per tract (safety net)  |
| `OSRM_MAX_WORKERS`         | 6       | Parallel OSRM request threads              |
