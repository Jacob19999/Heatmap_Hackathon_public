# Phase 0 Research: 004 Results Pipeline

## 1) Denominator and Geography Vintage Lock

**Decision**: Use ACS 5-year 2022 denominators with TIGER/Line 2022-compatible tract keys, USDA ERS RUCA (latest tract mapping available), and optional CDC/ATSDR SVI as a secondary overlay only.

- Total population denominator: ACS 5-year 2022 total population.
- Child population denominator: ACS 5-year 2022 population under 18 years (single consistent definition used across all pediatric metrics).
- Rurality classification: RUCA primary code with rural/urban grouping policy locked in config and documented in method notes.
- SVI: optional interpretive overlay; never part of core BEI pillars.

**Rationale**:

- Existing project artifacts and prior feature research already align on ACS 5-year 2022 and RUCA usage.
- A single denominator vintage improves reproducibility and avoids mixed-vintage joins.
- Constitution requires RUCA for rural/urban stratification and allows SVI only as secondary context.

**Alternatives considered**:

- **ACS 1-year**: rejected because tract-level stability/coverage is weaker for this use case.
- **Decennial-only denominators**: rejected for reduced comparability with existing augmentation flow.
- **SVI in core BEI**: rejected due to constitution requirement that need/context remain separate from core BEI.

## 2) Artifact Naming Convention Lock

**Decision**: Use a stage-centric primary naming convention with question-centric descriptors as suffixes/metadata.

Pattern:

`{stage_id}_{artifact_group}_{artifact_name}_{scenario}.{ext}`

Examples:

- `03_metrics_access_burden_by_ruca_ground_only.parquet`
- `04_tables_pediatric_gap_summary_ground_only.csv`
- `08_figures_hotspot_tiers_ground_only.png`
- `07_metrics_air_sensitivity_delta_ground_plus_air.parquet`

**Rationale**:

- Stage-centric prefixes make DAG lineage, reruns, and failure diagnostics immediate.
- Question-centric detail is preserved in artifact names and manifest metadata without losing stage traceability.
- Stable ordering by stage supports deterministic bundle construction.

**Alternatives considered**:

- **Question-centric primary naming only**: rejected; weak stage traceability in rerun/debug workflows.
- **Opaque hash/version naming**: rejected; hinders judge-facing transparency and manual inspection.

## 3) MVP Subset Policy Lock

**Decision**: Support exactly two orchestrated profiles for acceptance:

1. **MVP profile**: `00, 01, 02, 03, 04, 05, 08, 09` (minimum judge-ready baseline)
2. **Full profile**: `00-09` (includes structural-capacity competition and air-sensitivity stage)

Additionally, allow **developer exploratory reruns** via `run-stage`, but do not define `00-05`-only as a judge-acceptable profile.

**Rationale**:

- Preserves the user-requested sequencing and acceptance logic.
- Avoids diluting the definition of "complete challenge output" in hackathon review.
- Still supports fast iteration through targeted stage reruns.

**Alternatives considered**:

- **00-05 as accepted mini-MVP**: rejected; does not produce BEI hotspot and story-export artifacts.
- **Single full profile only**: rejected; reduces delivery reliability under hackathon time constraints.

## 4) Stage Contract and Output Validation Pattern

**Decision**: Every stage publishes declarative contract metadata and is validated against explicit artifact expectations before downstream execution.

Contract minimum:

- stage metadata (`stage_id`, `question`, dependencies)
- required input artifacts and schema expectations
- produced datasets/tables/figures/findings requirements
- validations list and stop-on-fail behavior

**Rationale**:

- Converts notebook convention into enforceable reproducible behavior.
- Supports independent stage reruns and consistent CI/pipeline checks.
- Keeps outputs formally auditable for judge-facing confidence.

**Alternatives considered**:

- **Implicit contracts in code comments only**: rejected; not machine-verifiable.
- **Validation only at final bundle step**: rejected; catches errors too late.

## 5) CLI Behavior and Failure Policy

**Decision**: Standardize CLI behavior for `run`, `run-stage`, `validate`, `list-stages`, and `build-final-exports` with non-zero exit on validation failure and explicit failure reporting.

**Rationale**:

- Meets acceptance requirement that failed validations halt downstream execution.
- Makes runs scriptable for local automation and repeatable demos.

**Alternatives considered**:

- **Best-effort continuation after validation failure**: rejected; risks silent methodological drift.

## 6) Clarification Resolution Summary

The three prior unresolved items are now fully resolved:

1. Denominator and RUCA/SVI vintage strategy: **locked** (ACS 2022 5-year + RUCA + optional SVI overlay).
2. Artifact naming strategy: **locked** (stage-centric primary naming).
3. Smaller-than-MVP accepted profile: **not accepted**; only MVP and full are official run profiles.
