# Data Model: 004 Results Pipeline

## Overview

This model defines the core entities, fields, relationships, and validation rules for a stage-based analytics pipeline that transforms NIRD plus approved augmentation layers into Challenge Area 3 outputs and final presentation artifacts.

## Entity: Facility

Represents a canonical facility record after Stage 00 cleaning and deduplication.

**Core fields**

- `facility_id` (string, required, unique)
- `source_facility_id` (string, required)
- `facility_name` (string, required)
- `address_line`, `city`, `state`, `zip` (string, required for geocoding)
- `latitude`, `longitude` (float, required post-geocoding)
- `designation_flags` (object/columns, required)
- `capability_flags` (object/columns, required)
- `total_beds` (numeric, required if available in NIRD)
- `burn_beds` (numeric, required if available in NIRD)
- `facility_class` (enum, required; derived in Stage 00)
- `is_pediatric_capable` (boolean, required)

**Validation rules**

- Deduplication must produce unique `facility_id`.
- Numeric bed fields must be coercible and non-negative.
- Missing coordinates after enrichment fail Stage 01 validation unless explicitly excluded with rationale.

## Entity: GeographicUnit

Represents tract/county/state units used for denominators, burden metrics, and rollups.

**Core fields**

- `geo_level` (enum: tract|county|state, required)
- `geoid` (string, required)
- `state_fips` (string, required)
- `county_fips` (string, required when applicable)
- `population_total` (numeric, required)
- `population_child_u18` (numeric, required for pediatric metrics)
- `ruca_primary_code` (numeric/string, required at tract level where available)
- `rural_urban_class` (enum, required for stratified outputs)
- `svi_overall` (numeric, optional)
- `geometry` (polygon/multipolygon, required for map-ready artifacts)

**Validation rules**

- `geoid` uniqueness is enforced within each `geo_level`.
- Denominator columns must be non-null for included analytic units.
- Rural/urban classification logic must be deterministic and documented.

## Entity: Scenario

Represents methodological assumptions used during stage execution.

**Core fields**

- `scenario_id` (enum: ground_only|ground_plus_air, required)
- `is_default` (boolean, required)
- `transport_mode_policy` (object, required)
- `transfer_penalty_minutes` (numeric, required for transfer-aware stages)
- `capacity_adjustment_policy` (object, optional)
- `air_assumptions` (object, required for ground_plus_air)

**Validation rules**

- Scenario IDs must be stable and present in config.
- Air assumptions must not be loaded for ground-only runs unless for comparative export.
- Scenario metadata must be propagated to all derived artifacts.

## Entity: StageContract

Represents required runtime metadata and contract declarations per stage.

**Core fields**

- `stage_id` (string, required, unique)
- `question` (string, required)
- `required_inputs` (array, required)
- `produced_datasets` (array, required, min 1)
- `produced_tables` (array, required, min 1)
- `produced_figures` (array, required, min 1)
- `validations` (array, required, min 1)
- `finding_template` (object/string, required)

**Validation rules**

- Stage cannot execute unless all `required_inputs` exist and pass schema checks.
- Stage cannot pass unless all produced artifact minimums are satisfied.
- Validation failure returns a non-zero status and blocks downstream stages.

## Entity: Artifact

Represents a persisted stage output tracked in manifests.

**Core fields**

- `artifact_id` (string, required, unique)
- `stage_id` (string, required)
- `artifact_type` (enum: dataset|table|figure|finding|manifest, required)
- `artifact_role` (string, required)
- `path` (string, required)
- `format` (enum subset: parquet|csv|json|geojson|png|md, required)
- `scenario_id` (string, required when scenario-sensitive)
- `created_at` (timestamp, required)
- `schema_version` (string, optional)

**Validation rules**

- Path must resolve inside approved output roots.
- Format/type pair must be valid (e.g., figure->png, dataset->parquet/csv).
- All final bundle artifacts must have manifest entries.

## Entity: FindingRecord

Represents machine-readable narrative output per stage.

**Core fields**

- `stage_id` (string, required)
- `question` (string, required)
- `finding` (string, required)
- `why_it_matters` (string, required)
- `action_implication` (string, required)
- `scenario_id` (string, optional but required for scenario-sensitive findings)

**Validation rules**

- All fields must be non-empty strings.
- Stage 09 final summary must include at least one finding for each final figure.

## Relationships

- A `StageContract` consumes and produces many `Artifact` records.
- A `Facility` belongs to one or more `GeographicUnit` contexts through enrichment joins.
- A `Scenario` influences many stage runs and therefore many artifacts.
- A `FindingRecord` references exactly one `stage_id` and may reference one `scenario_id`.

## Stage Transition Model

- `00 -> 01 -> 02 -> 03 -> 04 -> 05 -> 08 -> 09`
- `02 -> 06 -> 08`
- `02 -> 07 -> 08`

Transition rule: downstream stage starts only when all upstream required artifacts exist and pass validation.

## Data Integrity and Governance Rules

- Structural vs operational claims are encoded in labels/metadata and must propagate to outputs.
- Need overlays are separate entities/columns and cannot be merged into core BEI scoring fields.
- Pediatric metrics use child denominator fields and are stored separately from adult/general access measures.
