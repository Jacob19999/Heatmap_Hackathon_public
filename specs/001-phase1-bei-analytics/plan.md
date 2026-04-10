# Implementation Plan: Phase 1 — BEI Analytics Pipeline

**Branch**: `001-phase1-bei-analytics` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-phase1-bei-analytics/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Updated 2026-03-15 to reflect **air scenario: no Valhalla** — closest airport and straight-line distance only.

## Summary

Phase 1 delivers the Burn Equity Index (BEI) analytics pipeline: data foundation (NIRD + ACS + TIGER + RUCA), ground-only routing (Valhalla or OSRM) for tract–facility travel times, transfer-aware access, BEI components (S, T, P, C) and composite, conditional ground-plus-air sensitivity scenario, hotspot/clustering, and precomputed outputs. **Air scenario does not use Valhalla**: ground-to-launch and landing-to-facility legs use **closest airport by straight-line (Haversine) distance** and **estimated time = distance / configurable ground speed**; flight leg uses **straight-line distance / cruise speed**.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pandas, geopandas, numpy, scipy, scikit-learn, hdbscan, PySAL (esda, libpysal), matplotlib, seaborn, plotly, folium, openpyxl, shapely, requests, pyarrow, tqdm, cenpy  
**Storage**: File-based (Parquet tables, GeoJSON, Excel/CSV for NIRD and external data)  
**Testing**: pytest; `cd src; pytest; ruff check .`  
**Target Platform**: Workstation (Windows/macOS/Linux); Docker for Valhalla (ground routing only)  
**Project Type**: CLI / pipeline (Python modules under `src/`, run via `python -m src.pipeline.<module>`)  
**Performance Goals**: National tract-level matrix in bounded memory (chunked prefilter, incremental write); air scenario runs without routing API (Haversine only).  
**Constraints**: NIRD full file not readable by AI; routing backend required only for **ground** scenario; air scenario must run without Valhalla/OSRM.  
**Scale/Scope**: ~84k tracts, ~635 facilities, dual-path (MN high-detail tract + USA low-detail county).

**Air scenario (explicit)**:
- **Ground-to-launch**: For each tract, nearest FAA airport by **Haversine distance**; time = distance_km / `AIR_GROUND_SPEED_KMH` × 60 (minutes). No Valhalla/OSRM.
- **Landing-to-facility**: For each facility, nearest FAA airport by Haversine; same time formula.
- **Flight**: Haversine distance from launch airport to landing airport; time = distance_km / (cruise_speed_km_per_min). No routing API.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **§2.3 Challenge-Output Alignment**: Plan delivers outputs 1–5 (burn center distribution, rural/urban travel burden, pediatric access, burn-bed capacity, ground-only vs ground-plus-air). **PASS**
- **§4.4 Timely Access Transfer-Aware**: Ground-only routing uses road-network routing (Valhalla/OSRM); T component is transfer-aware. **PASS**
- **§4.5 Transport Scenario Policy**: Ground-only baseline + conditional ground-plus-air sensitivity. **PASS**
- **§4.6 Air-Access Honesty**: Air modeled as multi-stage (dispatch, ground-to-launch, flight, landing-to-facility, handoff); scenario-based, no claim of guaranteed transport. Air legs use closest airport and straight-line distance (documented). **PASS**
- **§7.2 Sensitivity Analysis**: Transfer penalty, air assumptions, cruise speed, capacity factor, catchment bands supported. **PASS**
- **§8 Phase 1 scope**: Data foundation, challenge outputs, ground-only routing, transfer-aware access, ground-plus-air scenario, BEI, sensitivity, visualizations, precomputed outputs. **PASS**

No unjustified violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-phase1-bei-analytics/
├── plan.md              # This file
├── research.md          # Phase 0 research (incl. air-scenario no-Valhalla decision)
├── data-model.md        # Entities, fields, relationships
├── quickstart.md        # Run instructions
├── contracts/           # presentation_manifest, product_views_manifest schemas
├── tasks.md             # Task breakdown (speckit.tasks)
└── checklists/          # requirements checklist
```

### Source Code (repository root)

```text
src/
├── pipeline/            # ingest, geocode, augment, routing, access, bei_*, aggregation, air_scenario, export, etc.
├── notebooks/           # Exploratory and challenge-output notebooks
tests/
```

**Structure Decision**: Single Python project under `src/` with pipeline modules; tests under `tests/`. Valhalla used only for ground routing (tract–facility and county–facility matrices). Air scenario is self-contained in `air_scenario.py` with no routing backend dependency.

## Complexity Tracking

None. All design choices align with constitution and spec.
