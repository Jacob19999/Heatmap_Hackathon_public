# Phase 1 Sanity-Check Gate (Constitution §8 / C1)

**Purpose**: Phase 2 Frontend MUST NOT start until this gate passes.  
**Feature**: 001-phase1-bei-analytics  
**Updated**: 2026-03-15

## Gate requirements (C1)

- [x] **§2.3 outputs validated**: Every §2.3 challenge output (burn center distribution, rural/urban travel burden, pediatric access, burn-bed capacity, ground-only vs ground-plus-air) has corresponding pipeline output and/or test.
- [x] **BEI sanity checks**: `pytest src/tests/test_sanity.py` and `src/pipeline/sanity_check.py` validate BEI formula, component bounds, tables, manifests, GeoJSON.
- [x] **Precomputed tables/GeoJSON**: MN tract BEI/access and USA county BEI/access tables and GeoJSON exist under `Data/output/`; product_views_manifest and profile manifests exist.
- [x] **No metric without §7.1 definition**: Metrics used in outputs are defined in research/spec (BEI, S/T/P/C, companion metrics).

## Phase 1 task status (T017–T020, T036–T037)

| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| T017 | Tract/county/state challenge-output aggregations in `aggregation.py` | **Done** | `aggregate_to_county`, `aggregate_to_state`; challenge metrics in `bei_composite.py`; covered by `test_direct_outputs.py`. |
| T018 | Pediatric and capacity companion metric helpers in `bei_components.py` | **Deferred** | Helpers live in `bei_composite.py` (e.g. `pediatric_access_per_capita`, burn-bed capacity). Move to `bei_components.py` only if refactor desired. |
| T019 | Export low-detail county companion tables in `export.py` | **Done** | County BEI and county access tables/GeoJSON exported for `usa_low_detail_county`; manifests reference them. |
| T020 | Document direct-output publication for both profiles in `quickstart.md` | **Done** | Quickstart includes dual-path build, verify outputs, and direct-output publication subsection. |
| T036 | County-level aggregation of air-scenario deltas in `aggregation.py` | **Done** | `aggregate_air_delta_to_county()`; pop-weighted rollup; covered by `test_air_sensitivity.py`. |
| T037 | Publish air-sensitivity scenario metadata and assets in `export.py` | **Done** | `ground_plus_air` in profiles and assets; delta table/GeoJSON paths when present; export writes delta GeoJSON from parquet. |

## How to run the gate

From repo root:

```bash
# 1. Sanity tests (BEI formula, component bounds, profile wiring)
pytest src/tests/test_sanity.py -v

# 2. Export contracts and sanity (manifests, schema, tables, GeoJSON)
cd src && pytest tests/test_export_contracts.py tests/test_sanity.py -v

# 3. Full pipeline sanity (after dual-path build)
python -m src.pipeline.sanity_check
```

**Gate PASS**: All of the above pass and Phase 1 gate checklist items above are satisfied (with T018 explicitly deferred).

## Deferred work (post–Phase 1 gate, before or with Phase 2)

- **T018**: Optional refactor to add pediatric/capacity helpers in `bei_components.py` (currently in `bei_composite.py`).

Phase 2 frontend may start once this gate passes; deferred items can be completed in parallel or in a follow-up Phase 1 patch.
