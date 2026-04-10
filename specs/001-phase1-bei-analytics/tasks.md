# Tasks: Phase 1 - BEI Analytics Pipeline

**Input**: Design documents from `specs/001-phase1-bei-analytics/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**C1 Gate**: Phase 2 Frontend MUST NOT start until the Phase 1 sanity-check gate passes. See [checklists/phase1_gate.md](checklists/phase1_gate.md) for the gate checklist and status of T017–T020, T036–T037.

**Tests**: Include focused regression and integration checks because the feature spec defines independent test criteria for each user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`)
- All task descriptions include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align shared profile/config/export plumbing with the dual-path product design.

- [X] T001 Finalize dual-profile defaults and aliases in `src/pipeline/presentation_scope.py`
- [X] T002 [P] Add county low-detail output path constants and manifest roots in `src/pipeline/config.py`
- [X] T003 [P] Extend shared manifest/export helpers for dual-path publication in `src/pipeline/export.py`
- [X] T004 [P] Add dual-path profile and manifest sanity checks in `src/tests/test_sanity.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared county-origin and low-detail routing foundation required before story implementation.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Implement county-origin analytic table helpers in `src/pipeline/aggregation.py`
- [X] T006 [P] Create the county-centroid Valhalla runner scaffold in `src/pipeline/usa_low_detail_county_valhalla.py`
- [X] T007 [P] Generalize routing input validation for tract and county origins in `src/pipeline/routing.py`
- [X] T008 [P] Generalize access-table helpers for tract and county geography keys in `src/pipeline/access.py`
- [X] T009 Add foundational county-origin and routing-shape tests in `src/tests/test_county_low_detail.py`

**Checkpoint**: County-origin infrastructure is ready and both profile paths can be implemented.

---

## Phase 3: User Story 1 - Data Foundation & Tract-Level Analytic Table (Priority: P1) 🎯 MVP

**Goal**: Produce the tract-level analytic table for the shared pipeline and the county-level analytic table needed for the USA low-detail fast path.

**Independent Test**: Run the ingestion/geocoding/augmentation flow and confirm facilities resolve to tracts, tract denominators are non-null, RUCA joins complete, and county-origin records have unique county FIPS plus non-null centroids.

### Tests for User Story 1

- [X] T010 [P] [US1] Add tract and county analytic table regression coverage in `src/tests/test_foundation_pipeline.py`

### Implementation for User Story 1

- [X] T011 [US1] Harden facility ingest and validation reporting in `src/pipeline/ingest.py`
- [X] T012 [P] [US1] Improve cached geocode merge and tract assignment handling in `src/pipeline/geocode.py`
- [X] T013 [P] [US1] Ensure tract analytic table exports required population, RUCA, and centroid fields in `src/pipeline/augment.py`
- [X] T014 [US1] Build county-level analytic table derivation from tract inputs in `src/pipeline/aggregation.py`
- [X] T015 [US1] Expose tract and county origin builders for downstream routing in `src/pipeline/mn_mvp_pipeline.py` and `src/pipeline/usa_low_detail_county_valhalla.py`

**Checkpoint**: US1 produces auditable tract and county origin tables for downstream analytics.

---

## Phase 4: User Story 2 - Challenge-Specific Direct Outputs (Priority: P2)

**Goal**: Compute publishable direct outputs at tract/county/state levels while supporting MN high detail and USA low detail views.

**Independent Test**: Verify zero-burn-center states remain zero in state summaries, rural travel burden exceeds urban burden, pediatric-capable access stays below general burn-center access, and county/state summaries publish correctly.

### Tests for User Story 2

- [X] T016 [P] [US2] Add direct-output aggregation regression checks in `src/tests/test_direct_outputs.py`

### Implementation for User Story 2

- [X] T017 [US2] Implement tract/county/state challenge-output aggregations in `src/pipeline/aggregation.py`
- [ ] T018 [P] [US2] Add pediatric and capacity companion metric helpers in `src/pipeline/bei_components.py` *(deferred: helpers live in bei_composite.py; deferral noted in checklists/phase1_gate.md)*
- [X] T019 [P] [US2] Export low-detail county companion tables for frontend use in `src/pipeline/export.py`
- [X] T020 [US2] Document direct-output publication for both profiles in `specs/001-phase1-bei-analytics/quickstart.md`

**Checkpoint**: US2 yields independent direct-output tables for the challenge deliverables.

---

## Phase 5: User Story 3 - Ground-Only Routing & Transfer-Aware Access (Priority: P3)

**Goal**: Keep MN high detail on tract routing while adding a true USA county-centroid to hospital Valhalla pipeline with transfer-aware access.

**Independent Test**: Confirm MN tract outputs reuse cached files when present, county-centroid Valhalla routing produces a county-to-hospital matrix, and direct vs transfer-aware system time obeys the better-of-direct-or-transfer rule for both geographies.

### Tests for User Story 3

- [X] T021 [P] [US3] Add routing and transfer-aware access tests for tract and county origins in `src/tests/test_routing_access.py`

### Implementation for User Story 3

- [X] T022 [US3] Preserve cached MN tract-detail reuse while cleaning profile naming in `src/pipeline/mn_mvp_pipeline.py`
- [X] T023 [P] [US3] Implement county-centroid Valhalla matrix generation in `src/pipeline/usa_low_detail_county_valhalla.py`
- [X] T024 [P] [US3] Add bounded-memory candidate prefiltering tuned for county origins in `src/pipeline/routing.py`
- [X] T025 [US3] Support county direct, transfer, and system travel times in `src/pipeline/access.py`
- [X] T026 [US3] Persist county travel-time matrix diagnostics and filled outputs in `src/pipeline/usa_low_detail_county_valhalla.py`
- [X] T027 [US3] Add command-line entrypoint and logging for the county low-detail route build in `src/pipeline/usa_low_detail_county_valhalla.py`

**Checkpoint**: US3 delivers working ground-only routing for both MN tract detail and USA county low detail.

---

## Phase 6: User Story 4 - BEI Components & Composite Index (Priority: P4)

**Goal**: Compute decomposable BEI outputs for both the Minnesota tract-detail path and the USA county-detail path.

**Independent Test**: Verify component bounds, composite decomposability, intuitive ordering for known good/bad geographies, and consistent county/state rankings from county-level low-detail outputs.

### Tests for User Story 4

- [X] T028 [P] [US4] Add BEI component and composite regression tests for county low-detail outputs in `src/tests/test_bei_dual_path.py`

### Implementation for User Story 4

- [X] T029 [US4] Generalize component computation for tract and county geographies in `src/pipeline/bei_components.py`
- [X] T030 [P] [US4] Generalize composite BEI calculation for dual-path outputs in `src/pipeline/bei_composite.py`
- [X] T031 [P] [US4] Compute county-level low-detail BEI from county access tables in `src/pipeline/usa_low_detail_county_valhalla.py`
- [X] T032 [US4] Produce county/state rollups for both profiles in `src/pipeline/aggregation.py`
- [X] T033 [US4] Write profile-aware BEI/access manifests for both paths in `src/pipeline/export.py`

**Checkpoint**: US4 yields decomposable BEI outputs for both frontend tabs.

---

## Phase 7: User Story 5 - Conditional Ground-Plus-Air Sensitivity Scenario (Priority: P5)

**Goal**: Add transparent air-sensitivity outputs while keeping the low-detail USA path compatible with county-level publication.

**Independent Test**: Confirm air paths improve access only where feasible, deltas are non-negative, and county/state summaries identify regions with meaningful air sensitivity.

### Tests for User Story 5

- [X] T034 [P] [US5] Add ground-vs-air delta regression tests in `src/tests/test_air_sensitivity.py`

### Implementation for User Story 5

- [X] T035 [US5] Complete tract-level air feasibility and path timing helpers in `src/pipeline/air_scenario.py`
- [X] T036 [P] [US5] Add county-level aggregation of air-scenario deltas in `src/pipeline/aggregation.py`
- [X] T037 [US5] Publish air-sensitivity scenario metadata and assets for both profiles in `src/pipeline/export.py`

**Checkpoint**: US5 exposes scenario-aware outputs without violating transport-assumption transparency.

---

## Phase 8: User Story 6 - ML Hotspot Discovery & Priority Layer (Priority: P6)

**Goal**: Detect hotspots and rank intervention priorities from validated BEI outputs.

**Independent Test**: Confirm hotspot clusters are statistically significant and spatially coherent, cluster archetypes are interpretable, and priority ranking changes when need overlays are applied.

### Tests for User Story 6

- [X] T038 [P] [US6] Add hotspot and priority regression checks in `src/tests/test_hotspot_priority.py`

### Implementation for User Story 6

- [X] T039 [US6] Compute hotspot statistics from tract and county BEI outputs in `src/pipeline/hotspot.py`
- [X] T040 [P] [US6] Implement clustering/archetype labeling in `src/pipeline/hotspot.py`
- [X] T041 [US6] Implement need-overlay priority ranking in `src/pipeline/priority.py`

**Checkpoint**: US6 yields actionable hotspot and priority layers for presentation.

---

## Phase 9: User Story 7 - Exploratory Visualizations & Precomputed Outputs (Priority: P7)

**Goal**: Export judge-ready payloads and visuals for both the MN high-detail and USA low-detail tabs.

**Independent Test**: Validate every figure renders, manifests resolve correctly, and exported tables/GeoJSON contain expected metric fields with non-null geography keys.

### Tests for User Story 7

- [X] T042 [P] [US7] Add manifest and export contract checks in `src/tests/test_export_contracts.py`

### Implementation for User Story 7

- [X] T043 [US7] Generate profile-aware tables and GeoJSON payloads in `src/pipeline/export.py`
- [X] T044 [P] [US7] Emit the default dual-tab product views manifest in `src/pipeline/export.py`
- [X] T045 [P] [US7] Create MN tract-detail and USA county-detail visual outputs in `src/pipeline/visualize.py`
- [X] T046 [US7] Update frontend handoff notes for both tabs in `src/frontend/challenge_area_3_frontend_backend_plan.md`
- [X] T047 [US7] Validate the documented dual-path run sequence in `specs/001-phase1-bei-analytics/quickstart.md`

**Checkpoint**: US7 completes the Phase 1 handoff to the frontend with precomputed assets and manifests.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Performance, documentation, and final validation across all stories.

- [X] T048 [P] Add dual-path performance guards and fallback warnings in `src/pipeline/routing.py`
- [X] T049 [P] Update metric definitions, assumptions, and limitations in `specs/001-phase1-bei-analytics/research.md`
- [X] T050 Run end-to-end validation for MN high detail and USA low detail builds via `specs/001-phase1-bei-analytics/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup**: No dependencies; start immediately.
- **Phase 2: Foundational**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; establishes tract and county analytic tables.
- **Phase 4 (US2)**: Depends on US1 outputs.
- **Phase 5 (US3)**: Depends on US1 and foundational routing helpers.
- **Phase 6 (US4)**: Depends on US2 and US3.
- **Phase 7 (US5)**: Depends on US3 and US4.
- **Phase 8 (US6)**: Depends on US4; benefits from US5 scenario outputs.
- **Phase 9 (US7)**: Depends on US2 through US6 for final published assets.
- **Phase 10: Polish**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: First independent increment after the foundation.
- **US2 (P2)**: Depends on the analytic tables from US1.
- **US3 (P3)**: Depends on US1 and foundational routing utilities; independent of US2 once origins exist.
- **US4 (P4)**: Depends on routing/access outputs from US3 and companion metrics from US2.
- **US5 (P5)**: Depends on US3/US4 baseline outputs.
- **US6 (P6)**: Depends on validated BEI outputs from US4.
- **US7 (P7)**: Depends on published outputs from US2-US6.

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel in Setup.
- `T006`, `T007`, and `T008` can run in parallel in Foundational.
- `T012` and `T013` can run in parallel in US1.
- `T018` and `T019` can run in parallel in US2.
- `T023` and `T024` can run in parallel in US3.
- `T030` and `T031` can run in parallel in US4.
- `T036` and `T037` can run in parallel in US5.
- `T040` and `T041` can run in parallel in US6.
- `T044` and `T045` can run in parallel in US7.

---

## Parallel Example: User Story 3

```bash
Task: "Implement county-centroid Valhalla matrix generation in src/pipeline/usa_low_detail_county_valhalla.py"
Task: "Add bounded-memory candidate prefiltering tuned for county origins in src/pipeline/routing.py"
```

## Parallel Example: User Story 7

```bash
Task: "Emit the default dual-tab product views manifest in src/pipeline/export.py"
Task: "Create MN tract-detail and USA county-detail visual outputs in src/pipeline/visualize.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: US1.
4. Complete Phase 5: US3.
5. Complete Phase 6: US4.
6. Complete Phase 9: US7.
7. Stop and validate the two-tab product with MN tract detail and USA county low detail.

### Incremental Delivery

1. Foundation first: shared dual-path profile, county-origin, and routing helpers.
2. Deliver US1 for auditable tract/county analytic tables.
3. Deliver US3 and US4 for the core dual-path routing + BEI outputs.
4. Deliver US7 for frontend-ready payloads and manifests.
5. Layer in US2, US5, and US6 for challenge outputs, air sensitivity, and hotspot analytics.

### Suggested MVP Scope

- Setup + Foundational
- US1 Data Foundation & Analytic Tables
- US3 Ground-Only Routing & Transfer-Aware Access
- US4 BEI Components & Composite Index
- US7 Exploratory Visualizations & Precomputed Outputs

---

## Notes

- All tasks follow the required checklist format with IDs, labels, and file paths.
- The USA low-detail design now assumes direct county-centroid Valhalla routing, not national tract aggregation.
- MN high detail remains tract-level and should continue reusing cached MN outputs when available.
