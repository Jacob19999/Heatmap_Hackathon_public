---

description: "Task list for Phase 7 Final Exports (Power BI CSV bundle)"
---

# Tasks: Phase 7 Final Exports

**Input**: Design documents from `C:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon\specs\005-powerbi-csv-exports\`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not requested in `spec.md` as automated TDD; verification follows each story’s **Independent Test** and `quickstart.md` manual steps.

**Organization**: Tasks are grouped by user story so each increment can be implemented and verified on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3)
- Every task includes exact file paths

## Path Conventions

- Bundle root: `Data/output/final_bundle/` (per `research.md`)
- Authoritative travel inputs: `Data/output/Travel Dist Processed/*.parquet` (per `research.md`)
- CLI: `src/results_pipeline/cli.py` with `build-final-exports` and `validate`
- Assembly logic: `src/results_pipeline/stages/stage_09_story_exports.py` (and related stages)
- Legacy/alternate export helpers: `src/pipeline/export.py`, `src/pipeline/rebuild_outputs.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align configuration and repository paths with the Phase 7 bundle contract before feature work.

- [ ] T001 Update `outputs` block in `configs/default.yaml` so `figures_dir`, `tables_dir`, `metrics_dir`, and `final_bundle_dir` resolve under `Data/output/` (including `Data/output/final_bundle/`) per `specs/005-powerbi-csv-exports/research.md` Decision 1
- [ ] T002 [P] Mirror the same `outputs` path conventions in `configs/mvp.yaml` and `configs/full.yaml` for consistent Phase 7 runs
- [ ] T003 [P] Align `src/results_pipeline/utils/paths.py` `PathLayout` defaults with `Data/output/` if any validation or tooling imports `build_layout()` during final-bundle workflows

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core path resolution, prerequisite diagnosis, and bundle-manifest machinery that **must** exist before user-story delivery.

**⚠️ CRITICAL**: No user story phase should be considered complete until this phase is done.

- [ ] T004 Refactor `_cfg()` in `src/results_pipeline/stages/stage_09_story_exports.py` so `figures_dir`, `tables_dir`, `metrics_dir`, and `final_bundle_dir` read from `RuntimeConfig` with defaults under `Data/output/` (not `outputs/`) when keys are absent
- [ ] T005 Refactor `_cfg()` in `src/results_pipeline/stages/stage_08_bei_hotspots.py` to use the same `outputs` path resolution rules as Stage 09 for `outputs_tables_dir`, `outputs_figures_dir`, `outputs_metrics_dir`, and `final_bundle_dir`
- [ ] T006 Update `_diagnose_final_export_inputs()` in `src/results_pipeline/orchestrator.py` to use the same resolved `figures_dir`, `tables_dir`, and `metrics_dir` as Stage 09 and to require the two filled travel Parquet files under `Data/output/Travel Dist Processed/` named in `specs/005-powerbi-csv-exports/quickstart.md`
- [ ] T007 Add a small validation module `src/results_pipeline/contracts/bundle_manifest_schema.py` that loads and validates JSON documents against `specs/005-powerbi-csv-exports/contracts/powerbi-bundle-manifest.schema.json`
- [ ] T008 Implement bundle manifest construction and write to `Data/output/final_bundle/powerbi_bundle_manifest.json` (or the filename required by the schema) in `src/results_pipeline/io/bundle_manifest.py`, mapping entities from `specs/005-powerbi-csv-exports/data-model.md` (`FinalBundle`, `ExportDataset`, `BundleManifestRecord`) into the schema’s `exports` array
- [ ] T009 Call the bundle manifest writer from `src/results_pipeline/stages/stage_09_story_exports.py` `run()` after core CSVs exist and validate the written JSON with `bundle_manifest_schema.py` before marking success

**Checkpoint**: Config and orchestration agree on `Data/output/`; Stage 09 can emit a schema-valid bundle manifest JSON.

---

## Phase 3: User Story 1 - Deliver a complete CSV export pack (Priority: P1) 🎯 MVP

**Goal**: Produce a full report-ingestion CSV set under `Data/output/final_bundle/` with business-facing names, stable columns, and summary/map/metrics views required for Power BI handoff.

**Independent Test**: Run `python -m src.results_pipeline.cli build-final-exports --config configs/default.yaml` on a completed results tree and confirm every required Phase 7 CSV listed in `specs/005-powerbi-csv-exports/quickstart.md` exists with documented fields and stable column names.

- [ ] T010 [US1] Extend `src/results_pipeline/stages/stage_09_story_exports.py` to emit `Data/output/final_bundle/top_hotspots.csv` when upstream hotspot outputs exist (sourcing from Stage 08 outputs or existing Parquet/CSV per plan), with columns and row grain documented in `method_notes.md` content from `_write_method_notes()`
- [ ] T011 [P] [US1] Add curated metrics CSV exports (tidy filters/aggregates for reporting) by reading existing Parquet/CSVs under `Data/output/tables/` and writing additional `*.csv` files into `Data/output/final_bundle/` via new helper functions in `src/pipeline/final_bundle_exports.py` (new file) or extended `src/pipeline/export.py`
- [ ] T012 [P] [US1] Add map-join tabular CSV exports (geography keys compatible with reporting layers) into `Data/output/final_bundle/` using the same helper layer, grounded in `spec.md` FR-005 and FR-006
- [ ] T013 [US1] Expand `final_findings_summary.csv`, `figure_manifest.csv`, and `table_manifest.csv` column sets in `src/results_pipeline/stages/stage_09_story_exports.py` so each row includes scenario labels, result-area tags, and plain-language purpose fields required by `spec.md` FR-002, FR-004, FR-007, and FR-012
- [ ] T014 [US1] Update `STAGE_META` strings in `src/results_pipeline/stages/stage_09_story_exports.py` so `required_inputs`, `produced_tables`, and `produced_figures` reference `Data/output/...` paths instead of legacy `outputs/...` literals
- [ ] T015 [US1] Ensure `build-final-exports` exit codes in `src/results_pipeline/cli.py` match `specs/005-powerbi-csv-exports/contracts/final-export-cli.md` for missing inputs (2), validation failures (3), and assembly failures (4)
- [ ] T016 [US1] On missing or empty required exports, fail with explicit messages listing artifact names in `src/results_pipeline/stages/stage_09_story_exports.py` and/or `src/results_pipeline/orchestrator.py`, satisfying `spec.md` FR-013 and FR-014

**Checkpoint**: Full CSV pack plus manifests and method notes exist under `Data/output/final_bundle/`; CLI failures are actionable.

---

## Phase 4: User Story 2 - Reproduce the same outputs reliably (Priority: P2)

**Goal**: Unchanged inputs yield the same file set, schemas, row grain, and naming; allowed metadata (e.g. timestamps) is isolated per `research.md` Decision 4.

**Independent Test**: Run `build-final-exports` twice with unchanged `Data/output/` inputs; compare file membership, CSV headers, and manifest `reproducibility` signatures (excluding allowed variable fields).

- [ ] T017 [US2] Implement input and schema signature helpers in `src/results_pipeline/io/reproducibility.py` (new file) that hash or fingerprint required source artifacts (including `Data/output/Travel Dist Processed/*.parquet`) and required export CSV schemas
- [ ] T018 [US2] Populate the `reproducibility` object in the bundle manifest per `specs/005-powerbi-csv-exports/contracts/powerbi-bundle-manifest.schema.json` inside `src/results_pipeline/io/bundle_manifest.py`, enumerating `allowed_variable_metadata` explicitly
- [ ] T019 [US2] Ensure CSV writers in `src/results_pipeline/io/writers.py` and Stage 09 use stable column ordering and formatting so two runs with identical inputs produce identical headers and row grain (isolate timestamp fields to allowed metadata only)
- [ ] T020 [US2] Extend `validate` behavior (via `validate_pipeline` / stage validation in `src/results_pipeline/orchestrator.py` and `src/results_pipeline/cli.py`) to report reproducibility drift when signatures do not match a stored previous manifest in `Data/output/final_bundle/` (if design stores last-run metadata there) or document single-run checks in `method_notes.md` via `_write_method_notes()` in `src/results_pipeline/stages/stage_09_story_exports.py`

**Checkpoint**: Two consecutive export runs show stable schemas and documented allowed metadata variance.

---

## Phase 5: User Story 3 - Package robustness evidence and traceability (Priority: P3)

**Goal**: Bundle includes robustness comparison CSVs, findings-to-artifact linkage, and reviewer traceability per `data-model.md` (`FindingsSummaryRecord`, `RobustnessComparison`).

**Independent Test**: Inspect `Data/output/final_bundle/` and confirm robustness CSVs, findings rows, and manifest records tie each headline metric to a result area and scenario.

- [ ] T021 [US3] Generate one or more robustness comparison CSV files under `Data/output/final_bundle/` (e.g. scenario deltas) using Stage 07 outputs or existing sensitivity tables, implemented in `src/results_pipeline/stages/stage_07_air_sensitivity.py` outputs consumed by `src/results_pipeline/stages/stage_09_story_exports.py` or a dedicated assembler in `src/pipeline/final_bundle_exports.py`
- [ ] T022 [US3] Add `findings_traceability.csv` (or equivalent) in `Data/output/final_bundle/` with columns matching `FindingsSummaryRecord` in `specs/005-powerbi-csv-exports/data-model.md`, produced in `src/results_pipeline/stages/stage_09_story_exports.py`
- [ ] T023 [US3] Ensure each figure/table referenced for reporting has a linked findings or manifest row by tightening `_validate_findings_coverage()` in `src/results_pipeline/stages/stage_09_story_exports.py` to cover Phase 7 artifact roles in `spec.md` FR-008–FR-010 and FR-018
- [ ] T024 [US3] Update `_write_method_notes()` in `src/results_pipeline/stages/stage_09_story_exports.py` to summarize robustness interpretation and constitution-aligned caveats (structural capacity, scenario labeling) for methodology reviewers

**Checkpoint**: Reviewer can trace exports to result areas and compare headline tables to robustness CSVs without extra transforms.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation accuracy, hygiene, and quickstart alignment.

- [ ] T025 [P] Reconcile command examples and expected paths in `specs/005-powerbi-csv-exports/quickstart.md` with implemented defaults in `configs/default.yaml` and actual bundle filenames under `Data/output/final_bundle/`
- [ ] T026 [P] Update `STAGE_META` in `src/results_pipeline/stages/stage_08_bei_hotspots.py` to list `Data/output/...` paths consistently with Stage 09
- [ ] T027 Run `ruff check .` from `src/` per `plan.md` and fix any new issues confined to touched Python modules
- [ ] T028 Execute the manual validation sequence in `specs/005-powerbi-csv-exports/quickstart.md` sections 1–4 against a machine with populated `Data/output/` artifacts and record any gaps as follow-up issues (no spec edits unless gaps are confirmed)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks** all user stories
- **Phase 3 (US1)**: Depends on Phase 2
- **Phase 4 (US2)**: Depends on Phase 2; practically depends on Phase 3 for complete CSV inventory to sign
- **Phase 5 (US3)**: Depends on Phase 2; requires headline exports from Phase 3 and sensitivity inputs where present
- **Phase 6 (Polish)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — delivers the MVP CSV pack
- **US2 (P2)**: After Phase 2; best after US1 artifacts are defined
- **US3 (P3)**: After Phase 2; builds on US1 traceability fields and available sensitivity outputs

### Within Each User Story

- Helpers (`src/pipeline/final_bundle_exports.py`, `src/results_pipeline/io/bundle_manifest.py`) before final wiring in Stage 09
- Core CSVs before manifest `exports` population
- Validation and CLI exit codes last within US1/US2

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run parallel with T001 after paths are agreed (different files)
- **Phase 2**: T007 parallel with T004–T006 if different authors (schema module vs stage refactors) — coordinate on shared interfaces
- **US1**: T011 and T012 parallel (different CSV outputs/helpers) once T010’s contract is clear
- **Polish**: T025 and T026 parallel

---

## Parallel Example: User Story 1

```bash
# After Stage 09 skeleton is stable, split CSV curation:
Task: "Add curated metrics CSV exports ... in src/pipeline/final_bundle_exports.py"
Task: "Add map-join tabular CSV exports ... in src/pipeline/final_bundle_exports.py"
```

---

## Parallel Example: User Story 2

```bash
# Signature helpers can be built alongside manifest wiring:
Task: "Implement input and schema signature helpers in src/results_pipeline/io/reproducibility.py"
Task: "Populate the reproducibility object ... in src/results_pipeline/io/bundle_manifest.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. **Stop and validate** using US1 **Independent Test** and `quickstart.md` build section

### Incremental Delivery

1. Setup + Foundational → bundle path and manifest validation ready
2. Add US1 → Power BI ingestion CSV pack
3. Add US2 → reproducibility signatures and stable rerun behavior
4. Add US3 → robustness and traceability tables
5. Polish → docs and repo hygiene

### Parallel Team Strategy

- Developer A: Phase 2 Stage 09 path refactor + orchestrator diagnostics
- Developer B: Bundle manifest schema module + JSON writer
- Developer C: `src/pipeline/final_bundle_exports.py` curated CSVs from Parquet

---

## Notes

- **[P]** tasks must not edit the same lines concurrently
- If git branch remains `004-results-pipeline`, set `SPECIFY_FEATURE=005-powerbi-csv-exports` or switch to the `005-powerbi-csv-exports` branch so Spec Kit scripts resolve this feature directory
- Constitution constraints (structural vs operational capacity, scenario honesty) must be reflected in `method_notes.md` and field labels, not only in prose specs

---

## Branch / FEATURE_DIR Note

`.\.specify\scripts\powershell\check-prerequisites.ps1 -Json` reported `FEATURE_DIR` as `...\specs\004-results-pipeline` because it derives the feature from the current git branch. This `tasks.md` is stored under `specs\005-powerbi-csv-exports\` to match **Phase 7** `plan.md` and `spec.md`. Align branch or `SPECIFY_FEATURE` before running Spec Kit hooks that depend on `FEATURE_DIR`.
