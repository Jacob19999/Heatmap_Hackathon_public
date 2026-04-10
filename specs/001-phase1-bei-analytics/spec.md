# Feature Specification: Phase 1 — BEI Analytics Pipeline

**Feature Branch**: `001-phase1-bei-analytics`
**Created**: 2026-03-14
**Status**: In Progress
**Input**: User description: "Implementation plan for Phase 1 — data processing, analytics, visualization (Python), and machine learning for the Burn Equity Index"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Data Foundation & Tract-Level Analytic Table (Priority: P1)

An analyst loads the NIRD dataset, validates it against the data dictionary, geocodes facilities to census tracts, and joins public augmentation layers (ACS population, TIGER/Line geometry, RUCA rurality codes) to produce a clean, tract-level analytic table that serves as the single source of truth for all downstream computation.

**Why this priority**: Every metric, visualization, and model depends on this table. Nothing downstream can run until the data foundation is validated and the geographic joins are auditable.

**Independent Test**: Run the pipeline end-to-end on the NIRD sample. Confirm that every facility maps to a census tract, population denominators are non-null for all tracts with population > 0, RUCA codes attach to every tract, and facility counts match known NIRD totals (135 burn centers, 617 trauma centers across 635 institutions).

**Acceptance Scenarios**:

1. **Given** the NIRD dataset and the data mapping document, **When** the analyst runs the ingestion pipeline, **Then** all fields match expected types, null counts are reported, and duplicate records are flagged
2. **Given** NIRD facility addresses, **When** geocoding is performed, **Then** at least 95% of facilities resolve to a valid latitude/longitude and census tract FIPS code. (Issue warning for missed facilities to resolve manually)
3. **Given** geocoded facilities and TIGER/Line shapefiles, **When** the spatial join runs, **Then** every facility is assigned to exactly one census tract with an auditable geographic key
4. **Given** ACS 5-year data, **When** population denominators are joined, **Then** every tract has total population and child population fields, and national totals are within 1% of published Census figures
5. **Given** RUCA codes, **When** joined to the tract table, **Then** every tract receives a rural/urban classification with no unmatched tracts

---

### User Story 2 — Challenge-Specific Direct Outputs (Priority: P2)

An analyst computes the four challenge-required direct outputs at tract, county, and state levels: burn center distribution per capita, rural versus urban travel burden, pediatric access relative to child population, and structural burn-bed capacity. These outputs are publishable independently of the composite BEI and directly address Challenge Area 3 deliverables.

**Why this priority**: These are the explicit deliverables for Challenge Area 3. They must work correctly and be interpretable before any composite index is built on top of them. They also provide the sanity-check benchmarks for the BEI.

**Independent Test**: Produce per-capita burn center counts by state and verify that states known to have zero burn centers (AK, DE, MS, MT, ND, NH, SD, WY) show zero. Produce rural vs urban travel burden and confirm rural tracts have systematically longer travel times. Produce pediatric access and confirm that pediatric-capable facility counts are lower than general burn-center counts.

**Acceptance Scenarios**:

1. **Given** the tract-level analytic table and burn-center designations, **When** burn centers per 100k population is computed per state, **Then** 8 states show zero and the national average is consistent with 135 centers / ~330M population
2. **Given** road-network travel times from the configured routing backend, **When** rural vs urban travel burden is computed, **Then** median travel time for rural (RUCA ≥ 4) tracts is significantly higher than for urban tracts, and a comparison table and distribution plot are produced
3. **Given** pediatric capability flags and child population, **When** pediatric access is computed, **Then** the number of pediatric-capable facilities is lower than general burn centers, and a per-capita pediatric access measure is produced at tract, county, and state levels
4. **Given** BURN_BEDS from NIRD and population, **When** structural burn-bed capacity per 100k is computed, **Then** results show meaningful variation across states, and a national map is producible

---

### User Story 3 — Ground-Only Routing & Transfer-Aware Access (Priority: P3)

An analyst computes road-network travel times from every census tract centroid to relevant facilities using a configurable routing backend (Valhalla default, OSRM-compatible), then builds both direct-access and transfer-aware access pathways. The transfer-aware formulation models the regionalized burn-care system where patients may first reach a stabilization-capable hospital before transferring to a definitive burn center.

**Why this priority**: The timely access burden (T) component — the most heavily weighted BEI pillar at 0.30 — depends on this routing. The ground-only baseline is also the default reporting scenario and must be correct before the air scenario is layered on.

**Independent Test**: For a known rural tract far from any burn center, verify that the transfer-aware system time is shorter than direct access time (because a stabilization hospital is closer). For a known urban tract near a burn center, verify direct access time is shorter. Confirm system time equals the minimum of direct and transfer-aware for every tract.

**Acceptance Scenarios**:

1. **Given** tract centroids and burn-center locations, **When** the routing backend computes drive times, **Then** a tract-to-facility travel-time matrix is produced for all candidate definitive burn centers and stabilization-capable hospitals within the configured catchment, with unreachable pairs retained as +∞, logged for diagnostics, and persisted in a chunked / streamed manner suitable for workstation-scale national runs
2. **Given** the travel-time matrix, **When** direct access time is computed, **Then** every tract has a minimum direct time to the nearest definitive burn center
3. **Given** stabilization hospitals, definitive centers, and a transfer penalty (default τ = 45 min), **When** transfer-aware access is computed, **Then** every tract has a system time equal to min(direct, stabilize + τ + transfer)
4. **Given** system times, **When** the stabilization tier penalty Δ is computed, **Then** tracts with no stabilization hospital within 30 minutes receive a positive penalty, and tracts with one nearby receive zero penalty
5. **Given** remaining unroutable tract-facility pairs, **When** matrix post-processing is run, **Then** a filled matrix is produced for downstream BEI work while preserving raw routed durations, fill provenance, and diagnostics

---

### User Story 4 — BEI Component Computation & Composite Index (Priority: P4)

An analyst computes the four BEI components (S, T, P, C) using the E2SFCA-style accessibility framework and step-decay function, normalizes them with robust min-max normalization (5th–95th percentile), and produces the composite BEI score at tract level. Companion metrics (nearest burn time, centers per 100k, beds per 100k, pediatric access score) are computed alongside.

**Why this priority**: The BEI is the central analytic product. It depends on US1–US3 being correct, but once those are in place, the BEI computation is the core deliverable that integrates everything.

**Independent Test**: Verify directionality: tracts in states with zero burn centers should rank in the top decile of BEI (worst equity). Verify decomposability: the sum of weighted components equals the composite. Verify that each component is bounded [0, 100]. Run against known good/bad geographies and confirm intuitive ordering.

**Acceptance Scenarios**:

1. **Given** the accessibility framework with facility capability weights, population, and step-decay (30/60/90 min bands), **When** specialized supply scarcity (S) is computed, **Then** every tract has an S score in [0, 1] and tracts far from any burn center have high S
2. **Given** system travel times from US3, **When** timely access burden (T) is computed as 0.75·Norm(T_sys) + 0.25·Norm(Δ), **Then** every tract has a T score in [0, 1] and transfer-dependent rural tracts have high T
3. **Given** pediatric capability weights and child population, **When** pediatric access gap (P) is computed, **Then** every tract has a P score in [0, 1] and regions without pediatric burn capability have high P
4. **Given** BURN_BEDS and population, **When** structural capacity gap (C) is computed, **Then** every tract has a C score in [0, 1] and low-bed regions have high C
5. **Given** all four components, **When** BEI = 100 × (0.25S + 0.30T + 0.20P + 0.25C) is computed, **Then** every tract has a BEI in [0, 100], higher = worse equity, and national distribution shows meaningful spread
6. **Given** companion metrics, **When** aggregated to county and state levels using population-weighted averages, **Then** all aggregation levels produce consistent rankings

---

### User Story 5 — Conditional Ground-Plus-Air Sensitivity Scenario (Priority: P5)

An analyst adds the air-access sensitivity scenario using FAA airport/heliport data. Air transport is modeled as a multi-stage path (dispatch + ground-to-launch + flight + landing-to-facility + handoff) with explicit, documented assumptions. The analyst then re-runs BEI computation under the air scenario and computes scenario deltas to show where air access materially changes equity estimates.

**Why this priority**: Transport scenario comparison is a required product feature (Constitution Section 2.3, output 5). It adds analytic depth and novelty but depends on the ground-only baseline being validated first.

**Independent Test**: For a remote rural tract, confirm that the air scenario produces a meaningfully shorter system time than the ground-only scenario. For a dense urban tract near a burn center, confirm the air scenario makes little difference. Verify that scenario deltas are non-negative (air never makes access worse).

**Acceptance Scenarios**:

1. **Given** FAA airport/heliport records, **When** launch and landing infrastructure is identified near tract centroids and facilities, **Then** a feasibility layer marks which origin-destination pairs have plausible air access
2. **Given** the air decomposition formula with explicit dispatch, ground-to-launch, flight (distance / cruise speed), landing-to-facility, and handoff parameters, **When** air travel times are computed, **Then** every feasible air path has a total time and every infeasible pair is marked as +∞
3. **Given** ground-only BEI and ground-plus-air BEI, **When** scenario deltas are computed, **Then** a delta table shows BEI improvement (or no change) for every tract, and a summary highlights the tracts where air access produces the largest equity improvement
4. **Given** scenario deltas, **When** aggregated to county and state levels, **Then** regions with large air-access sensitivity are identifiable and the distribution of deltas is visualizable

---

### User Story 6 — ML Hotspot Discovery & Priority Layer (Priority: P6)

An analyst uses spatial statistics (Getis-Ord Gi*, Local Moran's I) to detect statistically significant BEI hotspot clusters, then applies clustering (K-means, hierarchical, HDBSCAN) to discover hotspot archetypes (e.g., "rural transfer-burden hotspot," "pediatric access desert," "capacity-poor region"). A separate priority layer combines BEI with a need overlay to rank intervention priorities.

**Why this priority**: Hotspot discovery transforms the BEI from a raw score into actionable insights. It answers "what kind of problem does each place have?" rather than just "how bad is it?" This is a high-impact differentiator for judges but depends on validated BEI scores.

**Independent Test**: Confirm that Gi* hotspot clusters are spatially contiguous and statistically significant (p < 0.05). Confirm that cluster archetypes have interpretable profiles (e.g., one cluster has high T but low S, another has high P). Confirm that priority rankings shift when the need overlay is applied.

**Acceptance Scenarios**:

1. **Given** tract-level BEI scores and tract geometry, **When** Getis-Ord Gi* is computed, **Then** statistically significant (p < 0.05) high-BEI and low-BEI clusters are identified and mappable
2. **Given** tract BEI and component profiles [S, T, P, C, companion metrics, RUCA], **When** clustering is applied, **Then** 4–8 interpretable archetype clusters emerge with distinct component signatures
3. **Given** BEI and a need overlay (population + child population), **When** Priority = BEI × (1 + λ·NeedOverlay) is computed, **Then** high-population high-BEI tracts rank higher in priority than low-population high-BEI tracts
4. **Given** multiple BEI parameter scenarios (τ = 30/45/60, u = 1.0/0.75), **When** hotspot stability is tested, **Then** persistent hotspots (appearing in ≥ 80% of scenarios) are distinguished from conditional hotspots

---

### User Story 7 — Exploratory Visualizations & Precomputed Outputs (Priority: P7)

An analyst produces Python-based exploratory visualizations for every major analytic output (choropleth maps, distribution plots, scatter comparisons, rural/urban stratifications, scenario deltas) and generates precomputed output tables and map-ready GeoJSON payloads suitable for consumption by the Phase 2 frontend.

**Why this priority**: Visualizations serve as both the sanity-check mechanism for Phase 1 and the foundation for the Phase 2 frontend. Precomputed outputs are the handoff artifact that enables Phase 2 to begin.

**Independent Test**: Every visualization renders without errors and is labeled with title, legend, units, and data source. Every precomputed table has documented columns and no null keys. GeoJSON payloads load in a standard viewer and contain all metric fields.

**Acceptance Scenarios**:

1. **Given** tract-level BEI scores and geometry, **When** a national choropleth map is produced, **Then** it renders correctly with a color scale, legend, title, and interpretive caption
2. **Given** rural/urban stratification, **When** distribution comparison plots are produced, **Then** they show clear separation between rural and urban travel burden distributions
3. **Given** ground-only and ground-plus-air BEI, **When** a scenario delta map is produced, **Then** it highlights regions where air access makes the largest difference
4. **Given** all computed metrics, **When** precomputed output tables are exported, **Then** tract-level, county-level, and state-level CSV/Parquet files contain BEI, all four components, companion metrics, RUCA class, transport scenario, and geographic keys
5. **Given** tract geometry and metrics, **When** GeoJSON payloads are generated, **Then** files are valid GeoJSON, contain all metric fields as properties, and render in a standard GeoJSON viewer

---

### Edge Cases

- **Facilities with missing coordinates**: Hospitals that cannot be geocoded MUST be logged and excluded from spatial analysis with a documented count and impact assessment
- **Tracts with zero population**: Zero-population tracts (e.g., water bodies, parks) MUST be excluded from BEI computation and flagged in outputs
- **Tracts with no facility within 90 minutes**: These tracts receive maximum (worst) scores for access-dependent components; the count of such tracts MUST be reported
- **Routing-backend failures**: If the routing engine returns no path for a tract-facility pair, the pair is treated as unreachable (+∞); failure counts MUST be logged, and downstream matrix-filling steps MUST preserve the raw routed value and fill provenance
- **Workstation resource limits**: National routing runs MUST avoid materializing full dense origin-destination matrices, full request queues, or full Python-object result sets in memory at once; chunked prefiltering and incremental output persistence are required
- **Air feasibility edge cases**: Tracts with no airport/heliport within a configurable ground-to-launch threshold are treated as air-infeasible for that scenario
- **Pediatric-only facilities**: Facilities with pediatric burn capability but no adult burn capability MUST be counted only in the P component, not S or C
- **Ties in ranking**: When multiple tracts share identical BEI scores, ranking MUST use a stable, documented tiebreaker (e.g., alphabetical FIPS code)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ingest the NIRD dataset and validate all fields against the data mapping document, producing a structured validation report
- **FR-002**: System MUST geocode all NIRD facilities to latitude/longitude and census tract FIPS codes, logging failures and match rates
- **FR-003**: System MUST join ACS 5-year total population and child population to every census tract
- **FR-004**: System MUST join TIGER/Line census tract geometries for spatial analysis and mapping
- **FR-005**: System MUST join RUCA codes to every census tract for rural/urban classification
- **FR-006**: System MUST compute road-network travel times between tract centroids and all burn centers / stabilization hospitals within a configurable catchment (default 90 minutes) using a routing engine
- **FR-006A**: System MUST execute national-scale routing in bounded memory by chunking spatial prefilter work, limiting in-flight routing requests, and persisting matrix outputs incrementally instead of materializing the full dense routing workload in RAM
- **FR-007**: System MUST compute direct access time, transfer-aware access time, and system time for every tract under the ground-only scenario
- **FR-008**: System MUST compute the four BEI components (S, T, P, C) using the E2SFCA-style framework with configurable step-decay bands (default 30/60/90 min)
- **FR-009**: System MUST compute composite BEI = 100 × (0.25S + 0.30T + 0.20P + 0.25C) with higher = worse equity
- **FR-010**: System MUST normalize all raw component values using robust min-max normalization (5th–95th percentile winsorization)
- **FR-011**: System MUST compute companion metrics: nearest burn time, centers per 100k, beds per 100k, and pediatric access score
- **FR-012**: System MUST produce population-weighted aggregations at county and state levels for BEI and all components
- **FR-013**: System MUST compute the conditional ground-plus-air scenario using FAA airport/heliport data with explicit multi-stage air-path assumptions
- **FR-014**: System MUST compute scenario deltas (ground-only BEI minus ground-plus-air BEI) for every tract
- **FR-015**: System MUST detect spatial hotspot clusters using Getis-Ord Gi* and Local Moran's I with statistical significance thresholds
- **FR-016**: System MUST cluster tract profiles into interpretable archetypes using at least one unsupervised method
- **FR-017**: System MUST compute a separate priority layer that combines BEI with a need overlay, kept outside the core BEI
- **FR-018**: System MUST run sensitivity analyses varying transfer penalty (30/45/60 min), capacity utilization factor (1.0/0.75), and catchment bands
- **FR-019**: System MUST produce Python-based exploratory visualizations for every major output: national choropleth, distribution plots, rural/urban comparisons, scenario delta maps, hotspot maps, archetype maps
- **FR-020**: System MUST export precomputed output tables (tract/county/state) and map-ready GeoJSON payloads with all metric fields
- **FR-021**: System MUST document every metric with a formal definition, source inputs, directionality, scenario assumptions, plain-language interpretation, and limitations
- **FR-022**: System MUST log data lineage from raw NIRD through every join and computation step to final outputs

### Key Entities

- **Facility**: A hospital from NIRD, with geographic coordinates, burn/trauma designation, pediatric capability, bed counts, and capability weight
- **Census Tract**: The geographic unit of analysis, carrying population, child population, RUCA class, geometry centroid, and all computed metrics
- **Travel-Time Matrix**: Origin (tract centroid) to destination (facility) travel times by transport mode and scenario
- **BEI Record**: A tract-level record containing S, T, P, C component scores, composite BEI, companion metrics, transport scenario, and geographic keys
- **Hotspot Cluster**: A group of spatially contiguous tracts with statistically significant high BEI, carrying an archetype label and stability score
- **Precomputed Payload**: A tract/county/state-level export file containing all metrics, components, and geographic keys ready for frontend consumption

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The analytic table covers ≥ 99% of U.S. census tracts with non-null population, geography, and rurality classification
- **SC-002**: Facility geocoding resolves ≥ 95% of NIRD records to a valid census tract
- **SC-003**: The 8 states with zero burn centers (AK, DE, MS, MT, ND, NH, SD, WY) rank in the top quartile of state-level BEI (worst equity), confirming directional validity
- **SC-004**: Rural tracts (RUCA ≥ 4) have statistically higher median BEI than urban tracts (RUCA 1–3), confirming the model captures rural-urban disparities
- **SC-005**: Transfer-aware system time is ≤ direct access time for every tract (by construction), and ≥ 10% of rural tracts benefit meaningfully (> 15 min improvement) from the transfer pathway
- **SC-006**: Ground-plus-air scenario produces measurably lower BEI than ground-only for ≥ 5% of tracts, demonstrating the air scenario adds analytic value
- **SC-007**: Getis-Ord Gi* identifies ≥ 3 statistically significant (p < 0.05) national hotspot regions
- **SC-008**: Clustering produces 4–8 interpretable archetypes where each archetype has a distinguishable component profile (no two archetypes have identical dominant components)
- **SC-009**: Sensitivity analysis across ≥ 6 parameter combinations produces variation in BEI rankings without pathological behavior (no tract jumps from top decile to bottom decile under reasonable parameter changes)
- **SC-010**: All precomputed outputs (tract/county/state CSVs + GeoJSON) pass schema validation with zero null geographic keys and all expected metric columns present
- **SC-011**: Every Python visualization renders without errors and includes title, legend, units, and data source annotation
- **SC-012**: End-to-end pipeline from raw NIRD to final precomputed outputs completes within a reasonable timeframe suitable for iterative development

### NIRD Data Access Constraint

The NIRD dataset exists in two files:

- **Full dataset**: `Data/NIRD 20230130 Database_Hackathon_full_ai_ignore.xlsx` — the complete NIRD. AI assistants MUST NOT read or inspect this file due to data governance requirements.
- **Sample subset**: `Data/NIRD 20230130 Database_Hackathon_sample.xlsx` — a small subsample. AI assistants MAY read this file for schema understanding, field inspection, and code development.

All production code MUST point to the full dataset (`Database_Hackathon_full_ai_ignore.xlsx`) as its input path. AI assistants MUST write code that loads from the full file, using the sample only as a reference for column names, types, and structure.

AI assistants ARE allowed to see and analyze debugging outputs, error messages, logs, summary statistics, and printed results produced by running code against the full dataset. The restriction applies only to directly reading the raw full-dataset file, not to observing pipeline outputs.

### Assumptions

- A self-hosted routing backend is available for national-scale matrix work; Valhalla is the preferred default and OSRM remains a compatible fallback
- ACS 5-year vintage 2022 or later is used for population denominators
- TIGER/Line vintage matches the ACS vintage for consistent tract boundaries
- FAA airport/heliport data is current within 2 years
- The default transfer penalty (τ = 45 min) is a structural routing parameter, not a clinical estimate
- Air cruise speed is a transparent, documented scenario parameter (not calibrated to real operational data)
- The step-decay function (1.0/0.60/0.30/0 at 30/60/90+ min) is used unless sensitivity analysis justifies alternatives

