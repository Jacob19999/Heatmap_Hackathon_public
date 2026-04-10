# Remaining Work & Tests — Phase 1 BEI Analytics

**Feature**: 001-phase1-bei-analytics  
**As of**: 2026-03-15

This document lists all **remaining** implementation and test work. Tasks already implemented in code but not yet checked in `tasks.md` are marked below and will be reflected in an updated task list.

---

## Summary


| Phase         | Implementation remaining                      | Tests remaining     |
| ------------- | --------------------------------------------- | ------------------- |
| Phase 3 (US1) | T011–T015 (harden/improve; some logic exists) | T010                |
| Phase 4 (US2) | T017–T020                                     | T016                |
| Phase 5 (US3) | **Done** (T022–T027)                          | T021                |
| Phase 6 (US4) | **Done** (T029–T033)                          | T028                |
| Phase 7 (US5) | T036–T037 (air delta aggregation + export)    | T034; T035 **Done** |
| Phase 8 (US6) | T039–T041 (hotspot/priority logic)            | T038                |
| Phase 9 (US7) | T043–T047                                     | T042                |
| Phase 10      | T048–T050                                     | —                   |


---

## Phase 3: User Story 1 — Data Foundation

### Tests to add

- **T010** — Add tract and county analytic table regression coverage in `src/tests/test_foundation_pipeline.py`.
  - **File does not exist yet.** Create it.
  - Assert: facilities resolve to tracts, tract denominators non-null, RUCA joins complete, county-origin records have unique county FIPS and non-null centroids (per US1 independent test).

### Implementation remaining

- **T011** — Harden facility ingest and validation reporting in `src/pipeline/ingest.py`.
- **T012** — Improve cached geocode merge and tract assignment in `src/pipeline/geocode.py`.
- **T013** — Ensure tract analytic table exports required population, RUCA, centroid fields in `src/pipeline/augment.py`.
- **T014** — Build county-level analytic table derivation from tract inputs in `src/pipeline/aggregation.py` (partially exists via `county_origins_from_tracts`; confirm it satisfies US1).
- **T015** — Expose tract and county origin builders for downstream routing in `mn_mvp_pipeline.py` and `usa_low_detail_county_valhalla.py` (already used; may just need explicit docs or minor cleanup).

---

## Phase 4: User Story 2 — Challenge-Specific Direct Outputs

### Tests to add

- **T016** — Add direct-output aggregation regression checks in `src/tests/test_direct_outputs.py`.
  - **File does not exist yet.** Create it.
  - Assert: zero-burn-center states remain zero, rural travel burden > urban, pediatric access below general burn-center access, county/state summaries publish correctly.

### Implementation remaining

- **T017** — Implement tract/county/state challenge-output aggregations in `src/pipeline/aggregation.py`.
- **T018** — Add pediatric and capacity companion metric helpers in `src/pipeline/bei_components.py`.
- **T019** — Export low-detail county companion tables for frontend in `src/pipeline/export.py`.
- **T020** — Document direct-output publication for both profiles in `quickstart.md`.

---

## Phase 5: User Story 3 — Ground-Only Routing & Transfer-Aware Access

### Tests to add

- **T021** — Add routing and transfer-aware access tests for tract and county origins in `src/tests/test_routing_access.py`.
  - **File does not exist yet.** Create it.
  - Assert: MN tract reuse when cached, county-centroid Valhalla matrix produced, system time = min(direct, transfer) for both geographies.

### Implementation

- **T022–T027** — **Implemented** (county Valhalla matrix, prefilter, county access, diagnostics, CLI with `--chunk`, `--merge-only`, `--restart-container`). Mark as done in `tasks.md`.

---

## Phase 6: User Story 4 — BEI Components & Composite Index

### Tests to add

- **T028** — Add BEI component and composite regression tests for county low-detail in `src/tests/test_bei_dual_path.py`.
  - **File does not exist yet.** Create it.
  - Assert: component bounds, composite decomposability, intuitive ordering, county/state rankings consistent.

### Implementation

- **T029–T033** — **Implemented** (county BEI from access in `usa_low_detail_county.run_usa_county_pipeline_from_matrix`, manifests in `run_dual_path_pipeline` and MN pipeline). Mark as done in `tasks.md`.

---

## Phase 7: User Story 5 — Air Sensitivity Scenario

### Tests to add

- **T034** — Add ground-vs-air delta regression tests in `src/tests/test_air_sensitivity.py`.
  - **File does not exist yet.** Create it.
  - Assert: air improves access only where feasible, deltas non-negative, county/state summaries show meaningful air sensitivity.

### Implementation remaining

- **T035** — **Implemented** (air_scenario.py: FAA load, ground-to-launch/landing-to-facility via closest airport + straight-line, compute_air_travel_times, attach_ground_plus_air_access, run_air_scenario, main with --mn-only). Mark as done in `tasks.md`.
- **T036** — Add county-level aggregation of air-scenario deltas in `src/pipeline/aggregation.py`.
- **T037** — Publish air-sensitivity scenario metadata and assets for both profiles in `src/pipeline/export.py`.

---

## Phase 8: User Story 6 — ML Hotspot & Priority Layer

### Tests to add

- **T038** — Add hotspot and priority regression checks in `src/tests/test_hotspot_priority.py`.
  - **File exists** with tests; confirm they satisfy US6 independent test (hotspot clusters significant and coherent, archetypes interpretable, priority changes with need overlay).

### Implementation remaining

- **T039** — Compute hotspot statistics from tract and county BEI in `src/pipeline/hotspot.py`.
- **T040** — Implement clustering/archetype labeling in `src/pipeline/hotspot.py`.
- **T041** — Implement need-overlay priority ranking in `src/pipeline/priority.py`.

---

## Phase 9: User Story 7 — Visualizations & Precomputed Outputs

### Tests to add

- **T042** — Add manifest and export contract checks in `src/tests/test_export_contracts.py`.
  - **File does not exist yet.** Create it.
  - Assert: figures render, manifests resolve, exported tables/GeoJSON have expected metrics and non-null geography keys.

### Implementation remaining

- **T043** — Generate profile-aware tables and GeoJSON payloads in `src/pipeline/export.py`.
- **T044** — Emit default dual-tab product views manifest (partially done in `write_default_dual_path_product_views_manifest`; confirm and complete).
- **T045** — Create MN tract-detail and USA county-detail visual outputs in `src/pipeline/visualize.py`.
- **T046** — Update frontend handoff notes in `src/frontend/challenge_area_3_frontend_backend_plan.md` (path may differ; create or update doc).
- **T047** — Validate documented dual-path run sequence in `quickstart.md`.

---

## Phase 10: Polish & Cross-Cutting

### Implementation remaining

- **T048** — Add dual-path performance guards and fallback warnings in `src/pipeline/routing.py`.
- **T049** — Update metric definitions, assumptions, limitations in `research.md`.
- **T050** — Run end-to-end validation for MN high detail and USA low detail per quickstart.

---

## Test Files to Create


| File                                    | Task | Purpose                                     |
| --------------------------------------- | ---- | ------------------------------------------- |
| `src/tests/test_foundation_pipeline.py` | T010 | US1: tract/county analytic table regression |
| `src/tests/test_direct_outputs.py`      | T016 | US2: direct-output aggregation regression   |
| `src/tests/test_routing_access.py`      | T021 | US3: routing and transfer-aware access      |
| `src/tests/test_bei_dual_path.py`       | T028 | US4: BEI component/composite for dual path  |
| `src/tests/test_air_sensitivity.py`     | T034 | US5: ground-vs-air delta regression         |
| `src/tests/test_export_contracts.py`    | T042 | US7: manifest and export contract checks    |


**Existing test files**: `test_sanity.py`, `test_county_low_detail.py`, `test_ingest.py`, `test_bei_components.py`, `test_hotspot.py`, `test_hotspot_priority.py`.

---

## Recommended order of work

1. **Update `tasks.md`** — Mark T022–T027, T029–T033, T035 as `[X]` so remaining work is accurate.
2. **Tests first (per story)** — Add T010, T016, T021, T028, T034, T042 in the test files above so each user story has regression coverage.
3. **US1 (Phase 3)** — T011–T015 if foundation gaps remain.
4. **US2 (Phase 4)** — T017–T020 for challenge direct outputs.
5. **US5 (Phase 7)** — T036–T037 for air delta aggregation and export.
6. **US6 (Phase 8)** — T039–T041 for hotspot and priority (tests in test_hotspot_priority.py may already cover).
7. **US7 (Phase 9)** — T043–T047 for export/visualize and handoff.
8. **Phase 10** — T048–T050 for polish and E2E validation.

