# Data Model: Phase 7 Final Exports

## Overview

This model defines the report-ingestion bundle for Phase 7. It focuses on curated CSV exports, traceability records, robustness tables, and reproducibility evidence built from the existing challenge outputs under `Data/output/`.

## Entity: FinalBundle

Represents one completed Phase 7 delivery bundle written to `Data/output/final_bundle/`.

**Core fields**

- `bundle_id` (string, required, unique)
- `created_at` (timestamp, required)
- `status` (enum: pending|complete|failed, required)
- `default_scenario` (enum: ground_only|ground_plus_air, required)
- `bundle_root` (string, required)
- `method_notes_path` (string, required)
- `findings_summary_path` (string, required)
- `manifest_path` (string, required)
- `source_profiles` (array of strings, required)
- `run_label` (string, required)

**Validation rules**

- Bundle cannot be `complete` unless all required export artifacts exist.
- Bundle paths must resolve under `Data/output/final_bundle/`.
- A complete bundle must include a manifest, findings summary, and method notes.

## Entity: ExportDataset

Represents one CSV file delivered for reporting or reviewer consumption.

**Core fields**

- `export_id` (string, required, unique)
- `bundle_id` (string, required)
- `export_name` (string, required)
- `artifact_role` (enum: metrics|map_join|summary|robustness|traceability, required)
- `result_area` (enum: distribution|travel_burden|pediatric_access|structural_capacity|scenario_sensitivity|composite_hotspots|cross_cutting, required)
- `scenario_id` (enum: ground_only|ground_plus_air|not_applicable, required)
- `row_grain` (string, required)
- `path` (string, required)
- `column_names` (array of strings, required)
- `row_count` (integer, required)
- `source_artifacts` (array of strings, required)
- `plain_language_purpose` (string, required)

**Validation rules**

- Every export dataset path must end in `.csv`.
- Column names must be stable and non-empty.
- `row_count` must be zero or greater; zero-row files require an explicit manifest note.
- Every export dataset must map to one `result_area` and one `artifact_role`.

## Entity: BundleManifestRecord

Represents one manifest row describing a delivered artifact in the final bundle.

**Core fields**

- `artifact_id` (string, required, unique)
- `bundle_id` (string, required)
- `artifact_type` (enum: csv|figure|manifest|note|geojson|parquet, required)
- `artifact_role` (string, required)
- `path` (string, required)
- `format` (string, required)
- `scenario_id` (enum: ground_only|ground_plus_air|not_applicable, required)
- `result_area` (string, required)
- `row_grain` (string, optional)
- `row_count` (integer, optional)
- `source_stage_or_profile` (string, required)
- `is_required` (boolean, required)

**Validation rules**

- Every required bundle artifact must have exactly one manifest record.
- Manifest paths must be relative to the bundle root or output root and must not be blank.
- Scenario-sensitive artifacts must not use `not_applicable`.

## Entity: FindingsSummaryRecord

Represents one plain-language finding linked to a report-ready artifact.

**Core fields**

- `finding_id` (string, required, unique)
- `bundle_id` (string, required)
- `result_area` (string, required)
- `scenario_id` (enum: ground_only|ground_plus_air|not_applicable, required)
- `headline` (string, required)
- `finding` (string, required)
- `why_it_matters` (string, required)
- `action_implication` (string, required)
- `linked_artifact_id` (string, required)

**Validation rules**

- Every final figure or report-driving summary view must have at least one linked findings record.
- All text fields must be non-empty and understandable without code context.
- Scenario-sensitive findings must carry a scenario label.

## Entity: RobustnessComparison

Represents a CSV-delivered comparison used to assess whether headline conclusions remain stable under key alternative assumptions or aggregation views.

**Core fields**

- `comparison_id` (string, required, unique)
- `bundle_id` (string, required)
- `comparison_type` (enum: scenario_delta|aggregation_delta|parameter_sensitivity, required)
- `primary_result_area` (string, required)
- `baseline_label` (string, required)
- `comparison_label` (string, required)
- `path` (string, required)
- `row_grain` (string, required)
- `stability_interpretation` (string, required)

**Validation rules**

- Every robustness comparison must be exportable as a CSV in the final bundle.
- Comparison labels must describe what changed between baseline and alternative views.
- Robustness artifacts must not replace the primary reporting outputs; they must complement them.

## Entity: ReproducibilityRecord

Represents bundle-level evidence used to evaluate stability across reruns.

**Core fields**

- `record_id` (string, required, unique)
- `bundle_id` (string, required)
- `input_signature` (string, required)
- `export_set_signature` (string, required)
- `schema_signature` (string, required)
- `allowed_variable_metadata` (array of strings, required)
- `is_stable_rerun` (boolean, required)
- `notes` (string, optional)

**Validation rules**

- `is_stable_rerun` is true only when the file set, row grain, and schemas match the previous run for unchanged inputs.
- Allowed variable metadata must be explicitly enumerated rather than implied.

## Relationships

- A `FinalBundle` contains many `ExportDataset` records.
- A `FinalBundle` contains many `BundleManifestRecord` records.
- A `FinalBundle` contains many `FindingsSummaryRecord` records.
- A `FinalBundle` may contain many `RobustnessComparison` records.
- A `FinalBundle` may contain one or more `ReproducibilityRecord` entries across repeated runs.
- Each `FindingsSummaryRecord` links to one manifest or export artifact.

## State Transitions

- `pending -> complete`: all required CSVs, findings, notes, and manifest records are generated and validated.
- `pending -> failed`: generation stops because one or more required exports are missing, invalid, or inconsistent.
- `complete -> complete`: rerun with unchanged inputs produces a stable new bundle version with matching file set and schemas.
- `complete -> failed`: subsequent validation detects drift, missing artifacts, or broken traceability.

## Integrity Rules

- Baseline and scenario outputs must remain separately labeled in exported CSVs and manifest rows.
- Structural-capacity exports must retain structural framing and must not imply live bed availability.
- Need overlays and contextual layers must remain identifiable as overlays rather than being silently merged into core result definitions.
- The bundle must be understandable to a report builder without requiring notebook inspection or hidden file renaming.
