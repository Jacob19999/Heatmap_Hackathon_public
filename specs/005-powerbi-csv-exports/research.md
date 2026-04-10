# Research: Phase 7 Final Exports

## Decision 1: Use `Data/output/final_bundle/` as the canonical final bundle root

**Decision**: The Phase 7 final export bundle will be assembled under `Data/output/final_bundle/`, with report-ingestion CSVs, manifests, robustness tables, and notes stored beneath that root.

**Rationale**:
- The current repository already writes all production artifacts under `Data/output/`, not `outputs/`.
- Existing code in `src/pipeline/config.py`, `src/pipeline/export.py`, and `src/pipeline/presentation_scope.py` is already rooted in `Data/output/`.
- Using the real path convention avoids an unnecessary migration before final exports are stabilized.
- A dedicated `final_bundle/` child keeps report-facing deliverables separate from intermediate Parquet, GeoJSON, and QA artifacts.

**Alternatives considered**:
- `outputs/final_bundle/`: Rejected because it conflicts with the repository’s real output root and would force parallel path conventions during a late delivery phase.
- Writing CSVs directly into `Data/output/tables/`: Rejected because it would mix report-ingestion artifacts with intermediate analytic tables and make bundle completeness harder to validate.

## Decision 2: Treat the filled travel-distance Parquets in `Data/output/Travel Dist Processed/` as the authoritative processed travel inputs

**Decision**: The canonical processed travel-distance inputs for Phase 7 reproducibility and validation are:
- `Data/output/Travel Dist Processed/valhalla_mn_hospitals_timedist_filled.parquet`
- `Data/output/Travel Dist Processed/usa_low_detail_county_county_travel_time_matrix_filled.parquet`

**Rationale**:
- These files now exist on disk and represent the processed, gap-filled versions of the travel matrices the user explicitly called out.
- Current code still references filled matrices under `Data/output/tables/`, which creates path drift and reproducibility ambiguity.
- Phase 7 needs one authoritative location for processed travel inputs so rerun checks and manifest generation do not depend on stale assumptions.

**Alternatives considered**:
- Continue treating `Data/output/tables/` as the effective source of filled matrices: Rejected because it hides the distinction between raw and filled travel data.
- Copy the filled matrices into both `tables/` and `Travel Dist Processed/`: Rejected because duplicate canonical sources would make rerun validation and provenance tracking weaker.

## Decision 3: Keep the final export pack CSV-first but source it from curated Parquet/manifests rather than raw intermediate outputs

**Decision**: Phase 7 will generate the Power BI ingestion pack as curated CSVs derived from the existing presentation-ready Parquet tables, manifests, findings, and final figures rather than exporting raw routing or notebook intermediates directly.

**Rationale**:
- Current repository outputs are predominantly Parquet-first and already include presentation-oriented tables such as tract/county BEI and access outputs.
- Power BI handoff needs stable, flat, business-facing CSVs rather than raw operational tables like exception logs or chunked routing diagnostics.
- Separating curated report-ingestion CSVs from raw intermediates preserves clarity for analysts and reviewers.

**Alternatives considered**:
- Convert every Parquet file under `Data/output/tables/` into CSV: Rejected because many current tables are operational, incomplete, or not intended for report consumers.
- Feed Power BI directly from Parquet: Rejected because the feature requirement is a full CSV pack for report generation and analyst handoff.

## Decision 4: Use a bundle manifest with reproducibility metadata as the authoritative completeness check

**Decision**: The final bundle will include a machine-readable manifest that records bundle-level metadata and one record per export artifact, including artifact role, scenario, source result area, row grain, row count, format, and relative path. Reproducibility checks will compare file membership, column schemas, and manifest metadata across reruns.

**Rationale**:
- Existing manifests capture some asset paths, but they do not yet provide a single final-bundle completeness contract for CSV exports and traceability materials.
- A bundle manifest lets `validate` and `build-final-exports` make deterministic pass/fail decisions without guessing which files should exist.
- Row counts, schema signatures, and stable relative paths provide practical reproducibility evidence without requiring byte-for-byte identity for files that may contain run timestamps.

**Alternatives considered**:
- Rely only on folder inspection and file names: Rejected because it is too fragile for automated validation and reviewer traceability.
- Require byte-for-byte identical output files across reruns: Rejected because generated timestamps or other allowed metadata can vary while the substantive export structure remains stable.

## Decision 5: Implement Phase 7 through the `results_pipeline` CLI contract but reuse existing `src/pipeline` export code

**Decision**: The external contract for Phase 7 remains the `results-pipeline` CLI, especially `build-final-exports` and `validate`, but the implementation should initially delegate to or wrap the working logic in `src/pipeline/` rather than waiting for the full stage-orchestrated package to exist.

**Rationale**:
- `src/results_pipeline/cli.py` is the intended user-facing command surface, but it is currently stubbed.
- The working export/manifests behavior already lives in `src/pipeline/export.py` and related modules.
- Reusing the existing implementation surface reduces delivery risk and keeps the plan focused on final exports, reproducibility, and robustness rather than a full architecture rewrite.

**Alternatives considered**:
- Block Phase 7 until the full `src/results_pipeline/` architecture from feature `004` is implemented: Rejected because it delays the core deliverable of report-ready CSV outputs.
- Continue using only notebook/manual export paths with no CLI wrapper: Rejected because it fails the reproducibility and handoff requirements.

## Decision 6: Test Phase 7 with artifact-level contract tests and rerun-stability checks

**Decision**: Phase 7 validation will emphasize artifact contract tests, manifest completeness checks, scenario-label checks, and rerun-stability tests over full end-to-end recomputation of upstream analytics.

**Rationale**:
- The feature is about packaging existing results correctly and reproducibly, not recomputing the entire analytic pipeline from scratch.
- Current codebase already has export-oriented tests in `src/tests/`, making artifact-focused test additions a natural fit.
- This approach gives faster feedback on schema drift, missing CSVs, and traceability regressions.

**Alternatives considered**:
- Depend exclusively on manual review of exported folders: Rejected because it is too error-prone for final delivery hardening.
- Make Phase 7 tests rerun all routing and BEI calculations every time: Rejected because it adds unnecessary runtime and couples export validation to unrelated upstream computation cost.
