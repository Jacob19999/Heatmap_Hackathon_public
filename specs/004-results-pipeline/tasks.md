# Tasks: 004 Results Pipeline

**Input:**

- `specs/004-results-pipeline/spec.md`
- `specs/004-results-pipeline/plan.md`

**Feature Branch:** `004-results-pipeline`  
**Date:** 2026-03-16

---

## Phase 0 — Research and decision locking

### Goal

Lock methodology and contract assumptions before scaffolding or stage implementation begins.

- T001 Create `specs/004-results-pipeline/research.md` with all planning decisions resolved from the spec and plan.
- T002 Document denominator source and vintage decisions in `specs/004-results-pipeline/research.md` (total population = ACS 5-year 2022; child population = ACS 5-year 2022, under 18).
- T003 Document RUCA as the canonical rurality classification source in `specs/004-results-pipeline/research.md`.
- T004 Document SVI as optional overlay-only context, excluded from core BEI construction, in `specs/004-results-pipeline/research.md`.
- T005 Document official run profiles in `specs/004-results-pipeline/research.md` (MVP = `00, 01, 02, 03, 04, 05, 08, 09`; Full = `00–09`).
- T006 Document artifact naming convention in `specs/004-results-pipeline/research.md` using stage-centric prefixes and descriptive suffixes.
- T007 Document structural-capacity labeling rules in `specs/004-results-pipeline/research.md` to prohibit real-time claims from NIRD.
- T008 Document air-sensitivity labeling rules in `specs/004-results-pipeline/research.md` to require explicit scenario labeling.
- T009 Define deterministic rerun expectations in `specs/004-results-pipeline/research.md`, including what may differ between reruns and what must remain stable.
- T010 Define cache policy for routing and scenario outputs in `specs/004-results-pipeline/research.md`.
- T011 Record dependency justification notes for core, optional, and de-prioritized libraries in `specs/004-results-pipeline/research.md`.

### Exit checkpoint

- T012 Review `specs/004-results-pipeline/research.md` against FR-013, FR-018, FR-019, FR-027, FR-028, FR-029, FR-030, and FR-035 for consistency.

---

## Phase 1 — Design and contracts

### Goal

Translate the feature spec into explicit runtime contracts, schemas, and user-facing execution docs.

- T013 Create `specs/004-results-pipeline/data-model.md`.
- T014 Define the `NIRD Facility` entity in `specs/004-results-pipeline/data-model.md`, including identifiers, capability/designation fields, structural capacity fields, and derived facility class fields.
- T015 Define the `Geographic Unit` entity in `specs/004-results-pipeline/data-model.md`, including stable keys, denominator attributes, RUCA, and optional SVI.
- T016 Define the `Scenario` entity in `specs/004-results-pipeline/data-model.md`, including profile/scenario labels and key methodological toggles.
- T017 Define the `Stage` entity in `specs/004-results-pipeline/data-model.md`, including contract metadata and DAG relationships.
- T018 Define the `Artifact` entity in `specs/004-results-pipeline/data-model.md`, including type, path, stage, scenario, and manifest metadata.
- T019 Define the `Finding` entity in `specs/004-results-pipeline/data-model.md`, including stage/question/finding/why_it_matters/action_implication fields.
- T020 Create `specs/004-results-pipeline/contracts/stage-findings.schema.json`.
- T021 Encode required finding fields in `specs/004-results-pipeline/contracts/stage-findings.schema.json` (`stage_id`, `question`, `finding`, `why_it_matters`, `action_implication`).
- T022 Add optional scenario metadata fields to `specs/004-results-pipeline/contracts/stage-findings.schema.json`.
- T023 Create `specs/004-results-pipeline/contracts/artifact-manifest.schema.json`.
- T024 Encode required artifact manifest fields in `specs/004-results-pipeline/contracts/artifact-manifest.schema.json` (`stage_id`, `question`, `artifact_type`, `scenario_label`, `path`, `schema_version`, `artifact_name`).
- T025 Add optional file metadata fields such as checksum, row count, file size, and created timestamp to `specs/004-results-pipeline/contracts/artifact-manifest.schema.json`.
- T026 Create `specs/004-results-pipeline/contracts/stage-contract.schema.json`.
- T027 Define required stage contract fields in `specs/004-results-pipeline/contracts/stage-contract.schema.json` (`stage_id`, `name`, `question`, `description`, `replaces_notebooks`, `required_inputs`, `produced_datasets`, `produced_tables`, `produced_figures`, `produced_findings`, `validations`).
- T028 Create `specs/004-results-pipeline/contracts/cli-contract.md`.
- T029 Document CLI commands and expected arguments/options in `specs/004-results-pipeline/contracts/cli-contract.md`.
- T030 Document expected exit codes and non-zero failure behavior in `specs/004-results-pipeline/contracts/cli-contract.md`.
- T031 Document validation stop-on-fail behavior in `specs/004-results-pipeline/contracts/cli-contract.md`.
- T032 Document config layering and scenario/profile handling in `specs/004-results-pipeline/contracts/cli-contract.md`.
- T033 Create `specs/004-results-pipeline/quickstart.md`.
- T034 Document MVP full-run usage in `specs/004-results-pipeline/quickstart.md`.
- T035 Document stage-level rerun usage in `specs/004-results-pipeline/quickstart.md`.
- T036 Document `validate`, `list-stages`, and `build-final-exports` usage in `specs/004-results-pipeline/quickstart.md`.

### Exit checkpoint

- T037 Review all design artifacts in `specs/004-results-pipeline` against the spec to confirm they are detailed enough to drive implementation tasks.

---

## Phase 2 — Scaffolding and orchestration core

### Goal

Build the package foundation, CLI shell, config system, stage registry, and DAG orchestration.

- [X] T038 Create package skeleton under `src/results_pipeline/`.
- [X] T039 Create `src/results_pipeline/__init__.py`.
- [X] T040 Create `src/results_pipeline/cli.py`.
- [X] T041 Create `src/results_pipeline/settings.py`.
- [X] T042 Create `src/results_pipeline/logging.py`.
- [X] T043 Create `src/results_pipeline/registry.py`.
- [X] T044 Create `src/results_pipeline/orchestrator.py`.
- [X] T045 Create `src/results_pipeline/contracts/artifacts.py`.
- [X] T046 Create `src/results_pipeline/contracts/schemas.py`.
- [X] T047 Create `src/results_pipeline/contracts/stage.py`.
- [X] T048 Create `src/results_pipeline/io/loaders.py`.
- [X] T049 Create `src/results_pipeline/io/writers.py`.
- [X] T050 Create `src/results_pipeline/io/cache.py`.
- [X] T051 Create `src/results_pipeline/utils/paths.py`.
- [X] T052 Create `src/results_pipeline/utils/plotting.py`.
- [X] T053 Create `src/results_pipeline/utils/validation.py`.
- [X] T054 Create `src/results_pipeline/utils/geography.py`.
- [X] T055 Create `src/results_pipeline/utils/routing.py`.
- [X] T056 Create `src/results_pipeline/utils/normalization.py`.
- [X] T057 Implement config loading from YAML in `src/results_pipeline/settings.py`.
- [X] T058 Implement layered config merge order (default, profile, scenario, CLI overrides) in `src/results_pipeline/settings.py`.
- [X] T059 Validate loaded config structure before execution begins in `src/results_pipeline/settings.py`.
- [X] T060 Implement path helpers that enforce relative, contract-based locations only in `src/results_pipeline/utils/paths.py`.
- [X] T061 Implement logging setup for stage start/end, validation status, and error summaries in `src/results_pipeline/logging.py`.
- [X] T062 Implement stage base class or protocol in `src/results_pipeline/contracts/stage.py`.
- [X] T063 Implement stage registry in `src/results_pipeline/registry.py`.
- [X] T064 Register canonical DAG dependencies in `src/results_pipeline/registry.py` or `src/results_pipeline/orchestrator.py`.
- [X] T065 Implement DAG resolution and ordered execution in `src/results_pipeline/orchestrator.py`.
- [X] T066 Implement `results-pipeline list-stages` in `src/results_pipeline/cli.py`.
- [X] T067 Implement CLI parsing for `results-pipeline run --config <path>` in `src/results_pipeline/cli.py`.
- [X] T068 Implement CLI parsing for `results-pipeline run-stage <stage_id> --config <path>` in `src/results_pipeline/cli.py`.
- [X] T069 Implement CLI parsing for `results-pipeline validate` in `src/results_pipeline/cli.py`.
- [X] T070 Implement CLI parsing for `results-pipeline build-final-exports` in `src/results_pipeline/cli.py`.

### Tests

- [X] T071 [P] Add unit tests for config loading and merging in `tests/unit/test_settings.py`.
- [X] T072 [P] Add unit tests for stage registry behavior in `tests/unit/test_registry.py`.
- [X] T073 [P] Add unit tests for DAG resolution order in `tests/unit/test_orchestrator.py`.
- [X] T074 [P] Add unit tests for CLI command parsing and exit behavior in `tests/unit/test_cli.py`.

### Exit checkpoint

- [X] T075 Verify `results-pipeline list-stages` returns all stages in DAG order with question and description fields.
- [X] T076 Verify orchestrator can resolve MVP and full run stage sequences from config.

---

## Phase 3 — Contracts, IO, and validation plumbing

### Goal

Implement common artifact writing, findings writing, schema validation, cache helpers, and stop-on-fail behavior.

- [X] T077 Implement artifact model classes in `src/results_pipeline/contracts/artifacts.py`.
- [X] T078 Implement schema helpers in `src/results_pipeline/contracts/schemas.py`.
- [X] T079 Implement stage manifest writer in `src/results_pipeline/io/writers.py`.
- [X] T080 Implement findings writer in `src/results_pipeline/io/writers.py`.
- [X] T081 Implement dataset/table/figure write helpers in `src/results_pipeline/io/writers.py`.
- [X] T082 Implement input loaders that respect config-defined paths in `src/results_pipeline/io/loaders.py`.
- [X] T083 Implement cache utilities for expensive intermediates in `src/results_pipeline/io/cache.py`.
- [X] T084 Implement validation helpers in `src/results_pipeline/utils/validation.py` for file existence, required fields, schema shape, artifact presence, and manifest completeness.
- [X] T085 Implement stop-on-fail pipeline behavior in `src/results_pipeline/orchestrator.py`.
- [X] T086 Implement descriptive validation exception types in `src/results_pipeline/utils/validation.py` or a dedicated errors module.
- [X] T087 Implement `results-pipeline validate` to inspect declared contracts without recomputing the full pipeline in `src/results_pipeline/cli.py` and `src/results_pipeline/orchestrator.py`.

### Tests

- [X] T088 [P] Add unit tests for manifest generation in `tests/unit/test_manifests.py`.
- [X] T089 [P] Add unit tests for findings schema generation/validation in `tests/unit/test_findings_schema.py`.
- [X] T090 [P] Add contract tests for artifact naming conventions in `tests/contract/test_artifact_naming.py`.
- [X] T091 [P] Add contract tests for stage contract completeness in `tests/contract/test_stage_contracts.py`.
- [X] T092 [P] Add tests for stop-on-fail behavior and non-zero exit codes in `tests/integration/test_validation_failures.py`.

### Exit checkpoint

- [X] T093 Verify that a failed validation prevents downstream execution and produces a descriptive error (via `results-pipeline validate` and `results-pipeline run`).
- [X] T094 Verify that every stage can declare outputs and validations through a common contract.

---

## Phase 4 — Stage 00: data audit and standardization

### Goal

Build the trust gate for NIRD ingestion and standardization.

- [X] T095 Create `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T096 Implement Stage 00 contract metadata (`stage_id`, `name`, `question`, `description`, `replaces_notebooks`, outputs, validations) in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T097 Implement NIRD workbook loading in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T098 Implement worksheet presence checks for NIRD in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T099 Implement required column checks for NIRD in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T100 Implement normalization of whitespace/padded values in flag columns in `src/results_pipeline/utils/normalization.py`.
- [X] T101 Implement normalization of common Yes/No encodings in `src/results_pipeline/utils/normalization.py`.
- [X] T102 Implement normalization of common 1/blank encodings in `src/results_pipeline/utils/normalization.py`.
- [X] T103 Implement coercion for ZIP, `TOTAL_BEDS`, and `BURN_BEDS` fields in `src/results_pipeline/utils/normalization.py` and wire into Stage 00.
- [X] T104 Implement facility deduplication policy in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T105 Implement facility class derivation (ABA verified burn, non-verified burn-capable, trauma-only, combined burn + trauma, pediatric-capable burn) in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T106 Implement Stage 00 data quality summary table export in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T107 Implement Stage 00 missingness or completeness figure export in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T108 Implement Stage 00 facility type figure export in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T109 Implement Stage 00 findings record export in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T110 Implement Stage 00 manifest export in `src/results_pipeline/stages/stage_00_data_audit.py`.
- [X] T111 Write `data/interim/nird_clean.parquet` from Stage 00 outputs.
- [X] T112 Write Stage 00 tables and figures using stage-centric naming under `outputs/tables/` and `outputs/figures/`.

### Tests

- [X] T113 [P] Add unit tests for normalization helpers in `tests/unit/test_normalization.py`.
- [X] T114 [P] Add unit tests for deduplication logic in `tests/unit/test_deduplication.py`.
- [X] T115 [P] Add integration test for Stage 00 independent run in `tests/integration/test_stage_00.py`.
- [X] T116 [P] Add contract test ensuring Stage 00 emits dataset/table/figure/findings/manifest in `tests/contract/test_stage_00_contract.py`.

### Exit checkpoint

- [X] T117 Verify Stage 00 runs independently and emits all required artifacts.
- [X] T118 Verify Stage 00 failures halt downstream execution cleanly.

---

## Phase 5 — Stage 01: geography enrichment and denominators

### Goal

Build the reusable geographic backbone for downstream supply and access analysis.

- [X] T119 Create `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T120 Implement Stage 01 contract metadata in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T121 Implement facility geography enrichment using stable geographic keys in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T122 Implement county FIPS assignment in `src/results_pipeline/utils/geography.py` and use in Stage 01.
- [X] T123 Implement tract FIPS assignment where supported by configured data in `src/results_pipeline/utils/geography.py` and use in Stage 01.
- [X] T124 Implement denominator loaders for ACS total population in `src/results_pipeline/io/loaders.py`.
- [X] T125 Implement denominator loaders for ACS child population under 18 in `src/results_pipeline/io/loaders.py`.
- [X] T126 Implement county denominator join logic in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T127 Implement tract denominator join logic in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T128 Implement RUCA join logic in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T129 Implement optional SVI overlay join logic in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T130 Implement reusable county denominator artifact export in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T131 Implement reusable tract denominator artifact export in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T132 Implement facility geography artifact export in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T133 Implement Stage 01 map or exploratory figure export in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T134 Implement Stage 01 findings record export in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.
- [X] T135 Implement Stage 01 manifest export in `src/results_pipeline/stages/stage_01_geography_enrichment.py`.

### Tests

- [X] T136 [P] Add unit tests for geography key helpers in `tests/unit/test_geography.py`.
- [X] T137 [P] Add integration test for Stage 01 independent run using Stage 00 outputs in `tests/integration/test_stage_01.py`.
- [X] T138 [P] Add validation tests for missing geography keys or denominator join failures in `tests/integration/test_stage_01_validation.py`.

### Exit checkpoint

- [X] T139 Verify Stage 01 outputs are sufficient inputs for Stages 02–09.
- [X] T140 Verify missing geography/denominator issues are surfaced clearly.

---

## Phase 6 — MVP analytic stages

### Goal

Implement the minimum judge-ready stage set.

### Stage 02 — supply distribution and capacity baseline

- T141 Create `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T142 Implement Stage 02 contract metadata in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T143 Implement aggregation logic for state, county, and region supply metrics in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T144 Implement normalized supply metrics in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py` (ABA verified burn centers per population, burn-capable facilities per population, pediatric-capable facilities per child population, burn beds per population).
- T145 Implement adult and pediatric supply output tables in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T146 Implement Stage 02 choropleth or ranked supply figure export in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T147 Implement Stage 02 capacity figure export in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T148 Implement Stage 02 findings record export in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T149 Implement Stage 02 manifest export in `src/results_pipeline/stages/stage_02_supply_capacity_baseline.py`.
- T150 Write processed supply/capacity dataset outputs from Stage 02 under `data/processed/`.

### Tests

- T151 [P] Add integration test for Stage 02 run using Stage 01 outputs in `tests/integration/test_stage_02.py`.
- T152 [P] Add contract test for Stage 02 output presence and naming in `tests/contract/test_stage_02_contract.py`.

---

### Stage 03 — ground access burden

- T153 Create `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T154 Implement Stage 03 contract metadata in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T155 Implement origin selection logic for county and/or tract centroids in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T156 Implement facility destination selection for verified and burn-capable care in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T157 Implement routing helper integration for ground travel-time estimation in `src/results_pipeline/utils/routing.py` and use in Stage 03.
- T158 Implement OD matrix caching behavior for Stage 03 in `src/results_pipeline/io/cache.py` and `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T159 Implement travel-time summary metrics by tract/county/state in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T160 Implement RUCA-level access summaries in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T161 Implement state-level access summaries in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T162 Implement population coverage threshold table export in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T163 Implement rural/urban travel burden figure export in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T164 Implement Stage 03 findings record export in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T165 Implement Stage 03 manifest export in `src/results_pipeline/stages/stage_03_ground_access_burden.py`.
- T166 Write processed ground access metrics dataset from Stage 03 under `data/processed/`.

### Tests

- T167 [P] Add unit tests for routing/cache helpers used by Stage 03 in `tests/unit/test_routing_cache.py`.
- T168 [P] Add integration test for Stage 03 independent rerun with upstream artifacts present in `tests/integration/test_stage_03.py`.
- T169 [P] Add validation test for missing routing data or cache inconsistencies in `tests/integration/test_stage_03_validation.py`.

---

### Stage 04 — pediatric access gap

- T170 Create `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T171 Implement Stage 04 contract metadata in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T172 Define pediatric-capable destination set in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T173 Implement pediatric denominator logic based on Stage 01 outputs in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T174 Implement pediatric travel metric calculations in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T175 Implement adult versus pediatric access comparison logic in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T176 Implement pediatric access gap table export in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T177 Implement pediatric versus adult comparison figure export in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T178 Implement Stage 04 findings record export in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T179 Implement Stage 04 manifest export in `src/results_pipeline/stages/stage_04_pediatric_access_gap.py`.
- T180 Write processed pediatric access gap dataset from Stage 04 under `data/processed/`.

### Tests

- T181 [P] Add integration test for Stage 04 run using Stage 03 and Stage 01 outputs in `tests/integration/test_stage_04.py`.
- T182 [P] Add validation test ensuring pediatric metrics remain separated from adult metrics in `tests/integration/test_stage_04_validation.py`.

---

### Stage 05 — transfer-aware system access

- T183 Create `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T184 Implement Stage 05 contract metadata in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T185 Define stabilization candidate facilities in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T186 Implement direct-to-definitive travel-time path logic in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T187 Implement stabilize-and-transfer path logic in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T188 Implement transfer penalty handling from config in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T189 Implement comparison metrics between direct-only and transfer-aware access in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T190 Implement Stage 05 comparison table export in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T191 Implement Stage 05 transfer-aware figure export in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T192 Implement Stage 05 findings record export in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T193 Implement Stage 05 manifest export in `src/results_pipeline/stages/stage_05_transfer_aware_access.py`.
- T194 Write processed transfer-aware access dataset from Stage 05 under `data/processed/`.

### Tests

- T195 [P] Add integration test for Stage 05 run using Stage 03 outputs in `tests/integration/test_stage_05.py`.
- T196 [P] Add validation tests for transfer-penalty scenario consistency in `tests/integration/test_stage_05_validation.py`.

---

### Stage 08 — BEI composite hotspots and driver breakdown

- T197 Create `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T198 Implement Stage 08 contract metadata in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T199 Implement standardized pillar construction for MVP mode in `src/results_pipeline/stages/stage_08_bei_hotspots.py` (supply, timely access, pediatric access, structural-capacity proxy from available MVP inputs).
- T200 Implement optional incorporation of Stage 06 and Stage 07 outputs when present in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T201 Implement BEI composite score calculation in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T202 Implement hotspot tier classification in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T203 Implement driver breakdown labels in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T204 Implement need overlay attachment logic without mixing overlays into core BEI in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T205 Implement BEI hotspot table export in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T206 Implement BEI map or ranked hotspot figure export in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T207 Implement Stage 08 findings record export in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T208 Implement Stage 08 manifest export in `src/results_pipeline/stages/stage_08_bei_hotspots.py`.
- T209 Write processed BEI/hotspot dataset from Stage 08 under `data/processed/`.
- T210 Write `outputs/final_bundle/top_hotspots.csv` from Stage 08 outputs.

### Tests

- T211 [P] Add integration test for Stage 08 in MVP mode in `tests/integration/test_stage_08_mvp.py`.
- T212 [P] Add validation test confirming overlays are not included in the BEI core score in `tests/integration/test_stage_08_overlay_validation.py`.
- T213 [P] Add validation test confirming Stage 08 tolerates absence of Stages 06 and 07 in `tests/integration/test_stage_08_optional_stages.py`.

---

### Stage 09 — robustness and story exports

- T214 Create `src/results_pipeline/stages/stage_09_story_exports.py`.
- T215 Implement Stage 09 contract metadata in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T216 Implement figure/table selection logic for final bundle in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T217 Implement polished final figure export logic in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T218 Implement one-line findings aggregation for final outputs in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T219 Implement figure manifest generation in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T220 Implement table manifest generation in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T221 Implement `outputs/final_bundle/final_findings_summary.csv` generation in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T222 Implement `outputs/final_bundle/method_notes.md` generation in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T223 Implement `outputs/final_bundle/deck_ready/` export assembly in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T224 Implement `outputs/final_bundle/map_ready/` export assembly in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T225 Implement `outputs/final_bundle/metrics_ready/` export assembly in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T226 Implement final bundle manifest or summary export in `src/results_pipeline/stages/stage_09_story_exports.py` if needed.
- T227 Implement Stage 09 findings record export in `src/results_pipeline/stages/stage_09_story_exports.py`.
- T228 Implement Stage 09 manifest export in `src/results_pipeline/stages/stage_09_story_exports.py`.

### Tests

- T229 [P] Add integration test for Stage 09 in MVP mode in `tests/integration/test_stage_09_mvp.py`.
- T230 [P] Add validation test ensuring every final figure/table has a corresponding plain-language finding in `tests/integration/test_stage_09_findings_coverage.py`.

### MVP exit checkpoint

- T231 Run full MVP integration test for `results-pipeline run --config configs/mvp.yaml` from the project root.
- T232 Verify `outputs/final_bundle/` contains all required artifacts for MVP acceptance.
- T233 Verify each final artifact is traceable to a stage, question, and finding through manifests.

---

## Phase 7 — Additive full-run stages

### Goal

Implement optional but high-value structural capacity and air sensitivity stages.

### Stage 06 — structural capacity competition

- [X] T234 Create `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T235 Implement Stage 06 contract metadata in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T236 Implement structural catchment construction logic in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T237 Implement structural accessibility/competition scoring logic in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T238 Implement interpretable companion structural-capacity metrics in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T239 Implement Stage 06 table export in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T240 Implement Stage 06 figure export in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T241 Implement Stage 06 findings record export in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T242 Implement Stage 06 manifest export in `src/results_pipeline/stages/stage_06_structural_capacity.py`.
- [X] T243 Write processed structural capacity dataset from Stage 06 under `data/processed/`.

### Tests

- [X] T244 [P] Add integration test for Stage 06 using Stage 02/01 outputs in `tests/integration/test_stage_06.py`.
- [X] T245 [P] Add validation test ensuring Stage 06 outputs are clearly structural, not real-time, in `tests/integration/test_stage_06_validation.py`.

---

### Stage 07 — air sensitivity scenario

- [X] T246 Create `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T247 Implement Stage 07 contract metadata in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T248 Implement ground-only baseline comparison logic for scenario analysis in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T249 Implement conditional ground-plus-air scenario logic in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T250 Implement scenario label propagation into Stage 07 outputs in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T251 Implement protection against overwriting ground-only baseline artifacts in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T252 Implement Stage 07 table export in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T253 Implement Stage 07 figure export in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T254 Implement Stage 07 findings record export in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T255 Implement Stage 07 manifest export in `src/results_pipeline/stages/stage_07_air_sensitivity.py`.
- [X] T256 Write processed air sensitivity dataset from Stage 07 under `data/processed/`.

### Tests

- [X] T257 [P] Add integration test for Stage 07 using `configs/scenarios/ground_plus_air.yaml` in `tests/integration/test_stage_07.py`.
- [X] T258 [P] Add validation test ensuring all Stage 07 outputs are explicitly scenario-labeled in `tests/integration/test_stage_07_validation_labels.py`.
- [X] T259 [P] Add validation test ensuring Stage 07 does not modify baseline ground-only artifacts in `tests/integration/test_stage_07_baseline_protection.py`.

### Full-run exit checkpoint

- [X] T260 Run full integration test for `results-pipeline run --config configs/full.yaml` from the project root.
- [X] T261 Verify Stage 08 and Stage 09 consume Stage 06 and Stage 07 outputs when present.

---

## Phase 8 — Configs, manifests, and execution profiles

### Goal

Finalize config files and ensure runtime profiles behave as specified.

- [X] T262 Create `configs/default.yaml` with shared defaults for data paths, logging, and profile settings.
- [X] T263 Create `configs/mvp.yaml` describing MVP profile stages and any MVP-specific settings.
- [X] T264 Create `configs/full.yaml` describing full profile stages and any full-run-specific settings.
- [X] T265 Create `configs/scenarios/ground_only.yaml` for baseline scenario assumptions.
- [X] T266 Create `configs/scenarios/ground_plus_air.yaml` for air sensitivity scenario assumptions.
- [X] T267 Encode MVP stage list in `configs/mvp.yaml` (00, 01, 02, 03, 04, 05, 08, 09).
- [X] T268 Encode full stage list in `configs/full.yaml` (00–09).
- [X] T269 Encode baseline scenario assumptions in `configs/scenarios/ground_only.yaml`.
- [X] T270 Encode air sensitivity scenario assumptions in `configs/scenarios/ground_plus_air.yaml`.
- [X] T271 Add config validation rules for missing/inconsistent scenario settings in `src/results_pipeline/settings.py` or `src/results_pipeline/utils/validation.py`.
- [X] T272 Add CLI test coverage for profile/scenario config resolution in `tests/unit/test_config_profiles.py`.

### Exit checkpoint

- [X] T273 Verify config layering produces deterministic execution plans and scenario labels.

---

## Phase 9 — Final validation, reproducibility, and release hardening

### Goal

Harden the pipeline for judge/reviewer trust and repeatability.

- [X] T274 Implement deterministic rerun validation checks for stable schemas and paths in `tests/integration/test_rerun_stability.py` or a dedicated script.
- [X] T275 Implement reproducibility test fixture for unchanged input reruns in `tests/integration/test_reproducibility.py`.
- [X] T276 Implement manifest stability checks across reruns in `tests/integration/test_manifest_stability.py`.
- [X] T277 Implement final bundle completeness check in `src/results_pipeline/stages/stage_09_story_exports.py` or a dedicated validator.
- [X] T278 Implement missing upstream artifact diagnostics for `build-final-exports` in `src/results_pipeline/orchestrator.py` or `src/results_pipeline/cli.py`.
- [X] T279 Implement concise pass/fail summaries for `results-pipeline validate` in `src/results_pipeline/cli.py` and `src/results_pipeline/orchestrator.py`.
- [X] T280 Add release-ready logging for stage durations and failure summaries in `src/results_pipeline/logging.py`.
- [X] T281 Review `outputs/final_bundle/method_notes.md` for any deviations from notebook logic and document clearly.
- [X] T282 Verify every stage documents notebook replacement mapping in its contract metadata in `src/results_pipeline/stages/*.py`.
- [X] T283 Verify all scenario-based outputs are labeled correctly in manifests and findings.
- [X] T284 Verify no outputs make patient-level or real-time bed claims from NIRD across findings and method notes.

### Final tests

- [X] T285 Run unit test suite (`cd src; pytest tests/unit`).
- [X] T286 Run contract test suite (`cd src; pytest tests/contract`).
- [X] T287 Run integration test suite (`cd src; pytest tests/integration`).
- [X] T288 Run MVP command from a clean configured workspace: `results-pipeline run --config configs/mvp.yaml`.
- [X] T289 Run full command from a clean configured workspace: `results-pipeline run --config configs/full.yaml`.
- [X] T290 Run `results-pipeline validate` from the project root.
- [X] T291 Run `results-pipeline list-stages` from the project root.
- [X] T292 Run `results-pipeline build-final-exports` from the project root.

### Final acceptance checkpoint

- [X] T293 Confirm SC-001 is satisfied by successful MVP one-command run.
- [X] T294 Confirm SC-002 is satisfied by stage-level independent execution.
- [X] T295 Confirm SC-003 is satisfied by stop-on-fail validation behavior.
- [X] T296 Confirm SC-004 is satisfied by stable rerun schemas and paths.
- [X] T297 Confirm SC-005 is satisfied by final findings coverage of final figures/tables.
- [X] T298 Confirm SC-006 is satisfied by methodological labeling and overlay separation.

---

## Parallel work suggestions

These tasks can run in parallel once their dependencies are satisfied:

- T299 [P] Plan and schedule work for `T071–T074` after scaffolding (`Phase 2`) starts.
- T300 [P] Plan and schedule work for `T088–T092` after contract plumbing (`Phase 3`) exists.
- T301 [P] Plan and schedule work for `T113–T116` during Stage 00 implementation.
- T302 [P] Plan and schedule work for `T136–T138` during Stage 01 implementation.
- T303 [P] Plan and schedule work for `T151–T152`, `T167–T169`, `T181–T182`, `T195–T196`, `T211–T213`, `T229–T230` once corresponding stages exist.
- T304 [P] Plan and schedule work for `T244–T245`, `T257–T259` during full-run stage implementation.

---

## Minimum implementation path

If you want the shortest judge-ready path, prioritize:

- T305 Execute `T001–T037` (research and design).
- T306 Execute `T038–T094` (scaffolding, contracts, IO, validation plumbing).
- T307 Execute `T095–T140` (Stages 00–01).
- T308 Execute `T141–T233` (MVP analytic stages 02, 03, 04, 05, 08, 09).
- T309 Execute `T262–T273` (configs and profiles).
- T310 Execute `T274–T298` (final validation, reproducibility, acceptance checks).

Then add:

- T311 Execute `T234–T261` (full-run structural capacity and air-sensitivity stages).

