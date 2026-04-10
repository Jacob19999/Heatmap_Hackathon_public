# Final Export CLI Contract: Phase 7

## Command Surface

All Phase 7 final export commands are exposed via:

- `results-pipeline <command> [options]`
- `python -m src.results_pipeline.cli <command> [options]`

## Commands

### 1) `build-final-exports`

Builds the complete report-ingestion bundle from already-produced challenge outputs.

**Input**

- `--config <path>` (required)

**Behavior**

- Resolves the dataset profile, scenario policy, and bundle destination from config.
- Reads existing validated artifacts under `Data/output/`.
- Produces `Data/output/final_bundle/` with required CSVs, findings summary, method notes, and manifest outputs.
- Fails if any required source artifact, required final CSV, or traceability record is missing.

**Exit codes**

- `0`: bundle created successfully
- `2`: config or required source input is missing/invalid
- `3`: validation or bundle completeness failure
- `4`: export assembly failure

### 2) `validate`

Validates the final export bundle or its prerequisites without recomputing upstream analytics.

**Input**

- `--config <path>` (optional if default config exists)

**Behavior**

- Verifies final-bundle prerequisites and, when present, validates the finished bundle.
- Checks artifact existence, required CSV coverage, schema stability markers, scenario labels, and findings/manifest completeness.
- Reports pass/fail status with actionable failure reasons.

**Exit codes**

- `0`: all checks pass
- `3`: one or more bundle validation checks fail
- `4`: validation runtime error

### 3) `run`

Runs the selected pipeline profile and may delegate to `build-final-exports` when the chosen profile includes final export assembly.

**Input**

- `--config <path>` (required)

**Behavior**

- Uses the broader pipeline contract when available.
- For Phase 7 scope, may call into the existing `src/pipeline/` export/manifests logic after prerequisite artifacts exist.

**Exit codes**

- `0`: success
- `2`: invalid config or missing prerequisites
- `3`: validation failure
- `4`: execution failure

## Global Contract Rules

- Final export assembly must be deterministic for unchanged inputs, aside from allowed run metadata.
- Scenario-sensitive outputs must be explicitly labeled in filenames, CSV fields, and manifest rows.
- Structural-capacity outputs must remain clearly labeled as structural rather than real-time.
- Every report-driving artifact must have a corresponding findings or manifest record.
- Validation failures are blocking; there is no best-effort partial success for a final bundle.
