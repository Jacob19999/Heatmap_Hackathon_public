# Feature Specification: 004 Results Pipeline

**Feature Branch**: `004-results-pipeline`  
**Created**: 2026-03-16  
**Status**: Draft  
**Input**: User description: "Build a feature called 004 results-pipeline that converts the existing Challenge Area 3 notebook stack into a reproducible Python analytics pipeline that generates all Challenge Area 3 outputs and supporting presentation artifacts from NIRD plus approved public augmentation layers."

The goal of this feature is to turn the existing Challenge Area 3 notebook stack into a reproducible, stage-based results pipeline that can regenerate all Challenge Area 3 outputs, figures, tables, maps, and findings from configured NIRD sources and approved public augmentation layers using a small set of CLI commands.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Regenerate full results bundle (Priority: P1)

As a **hackathon analyst**, I want to run a **single CLI command** that reads NIRD plus approved public augmentation layers and regenerates the **full Challenge Area 3 results bundle** (figures, tables, maps, findings) so that I can **quickly produce judge-ready outputs** from a fresh checkout or updated input data.

**Why this priority**: This is the primary hackathon workflow and the core acceptance criterion: judges must be able to regenerate the full story from configured sources with one command.

**Independent Test**: From a clean workspace with configured data paths, run `results-pipeline run --config configs/mvp.yaml` and verify that all required outputs in `outputs/final_bundle/` and stage-specific output contracts exist, pass validations, and match expected structure and naming.

**Acceptance Scenarios**:

1. **Given** a fresh checkout with NIRD and configuration files available, **When** the analyst runs `results-pipeline run --config configs/mvp.yaml`, **Then** all MVP stages (00, 01, 02, 03, 04, 05, 08, 09) complete successfully and produce the required datasets, tables, figures, and findings in stable, documented locations.
2. **Given** a previously run pipeline with existing outputs, **When** the analyst re-runs the same command with unchanged inputs, **Then** the outputs are regenerated deterministically (no missing files, consistent schemas, and no spurious differences beyond timestamps and metadata).

---

### User Story 2 - Rerun or extend specific stages (Priority: P2)

As a **pipeline developer or analyst**, I want to **run an individual stage** (for example, just the ground access burden or air sensitivity stage) using a shared configuration so that I can **iterate on a single question** (e.g., travel-time modeling) without rerunning the entire pipeline.

**Why this priority**: Efficient iteration by stage is critical for refining methodology, debugging, and exploring alternative scenarios (e.g., different air-transport assumptions) under time pressure.

**Independent Test**: With upstream outputs already generated, run `results-pipeline run-stage 03 --config configs/default.yaml` (or another stage) and verify that the stage completes, respects its declared input/output contract, and updates only its artifacts and findings.

**Acceptance Scenarios**:

1. **Given** that stages 00–02 have been successfully run, **When** the analyst runs `results-pipeline run-stage 03 --config configs/default.yaml`, **Then** stage 03 completes without re-running earlier stages and writes its datasets, tables, figures, and findings according to its contract.
2. **Given** that all prerequisites for stage 07 exist, **When** the analyst runs `results-pipeline run-stage 07 --config configs/scenarios/ground_plus_air.yaml`, **Then** the stage produces scenario-labeled air-sensitivity artifacts without affecting the primary ground-only outputs.

---

### User Story 3 - Validate pipeline readiness and outputs (Priority: P3)

As a **judge, reviewer, or methodologist**, I want to **inspect validation status, stage list, and final exports** so that I can **trust the methodological rigor** and understand how each stage answers a specific challenge question.

**Why this priority**: The hackathon rubric emphasizes methodological soundness, clarity, and actionability; judges must be able to see that the pipeline is well-structured, validated, and aligned with Challenge Area 3 expectations.

**Independent Test**: Run `results-pipeline validate`, `results-pipeline list-stages`, and `results-pipeline build-final-exports`, then inspect logs, validation reports, and final manifests to confirm that required stages are present, validations are enforced, and judge-facing artifacts are complete and clearly labeled.

**Acceptance Scenarios**:

1. **Given** a configured and runnable pipeline, **When** a reviewer runs `results-pipeline validate`, **Then** they receive a clear pass/fail summary per stage and any failed validations block downstream execution.
2. **Given** a successful full run, **When** a reviewer inspects `outputs/final_bundle/` (including `final_findings_summary.csv`, manifests, and method notes), **Then** they can trace each final figure/table back to a stage, question, and formal finding.

---

### Edge Cases

- Missing or incomplete NIRD input files (e.g., missing workbook tabs, unexpected column encodings).
- Public augmentation layers (Census, RUCA, SVI, routing data) unavailable or partially available for some geographies.
- Facilities with ambiguous or conflicting identifiers leading to potential duplicate or missing facilities.
- Scenarios where validations fail mid-pipeline (e.g., denominator totals inconsistent with NIRD counts) and should halt downstream stages with clear error messaging.
- Configuration that requests full run including 06 and 07 but scenario-specific configs are missing or inconsistent.

## Requirements *(mandatory)*

### Functional Requirements

**Pipeline structure and orchestration**

- **FR-001**: The system MUST implement a **stage-based results pipeline package** under `src/results_pipeline/` with the package structure and module layout described in the feature input (including `cli.py`, `settings.py`, `logging.py`, `contracts/`, `io/`, `utils/`, and `stages/` modules).
- **FR-002**: The system MUST support a **simple DAG orchestration model** where stages are executed in the canonical order  
  `00 -> 01 -> 02 -> 03 -> 04 -> 05 -> 08 -> 09`  
  with additional edges  
  `02 -> 06`, `02 -> 07`, and both 06 and 07 feeding into 08 for full runs.
- **FR-003**: Each stage module (`stage_00_...` through `stage_09_...`) MUST implement a **standard stage contract interface** exposing:
  - `stage_id`
  - `question`
  - `required_inputs`
  - `produced_datasets`
  - `produced_tables`
  - `produced_figures`
  - `validations`
  - `finding_template`
  - `run(config)`
- **FR-004**: The pipeline MUST support three primary CLI entrypoints:
  - `results-pipeline run --config <config_path>` for orchestrated multi-stage runs (MVP or full).
  - `results-pipeline run-stage <stage_id> --config <config_path>` for individual stage execution.
  - `results-pipeline validate`, `results-pipeline list-stages`, and `results-pipeline build-final-exports` for validation, discovery, and bundling.

**Configuration and scenarios**

- **FR-005**: The system MUST load configuration files from `configs/` (e.g., `default.yaml`, `mvp.yaml`, `full.yaml`) and `configs/scenarios/` (e.g., `ground_only.yaml`, `ground_plus_air.yaml`) to control:
  - data locations,
  - stage selection,
  - scenario flags (e.g., ground-only vs ground-plus-air),
  - and key methodological toggles.
- **FR-006**: The MVP configuration (`configs/mvp.yaml`) MUST be defined such that running `results-pipeline run --config configs/mvp.yaml` executes stages 00, 01, 02, 03, 04, 05, 08, and 09 and produces a complete Challenge Area 3 story.
- **FR-007**: The full configuration (`configs/full.yaml`) MUST be defined such that running `results-pipeline run --config configs/full.yaml` executes all stages (00–09), including structural capacity (06) and air sensitivity (07).
- **FR-008**: Scenario configuration files in `configs/scenarios/` MUST clearly indicate whether they represent **ground-only** or **conditional ground-plus-air** assumptions and MUST propagate scenario labels into outputs and findings.

**Data contracts and IO**

- **FR-009**: The system MUST define **formal data and artifact contracts** (schemas, locations, and naming) for:
  - raw, interim, and processed data under `data/`,
  - per-stage outputs under `outputs/`,
  - final bundle artifacts under `outputs/final_bundle/`.
- **FR-010**: Each stage MUST emit at least:
  - one **parquet or CSV dataset**,
  - one **exportable figure**,
  - one **exportable table**,
  - one **machine-readable findings record**, following the findings schema in the feature input.
- **FR-011**: The system MUST implement IO helpers (`loaders.py`, `writers.py`, `cache.py`) that:
  - respect the path conventions from `utils/paths.py`,
  - avoid hard-coded absolute paths,
  - and enable caching of expensive intermediate results when configured.

**Methodological requirements by stage**

- **FR-012**: Stage 00 (data audit and standardization) MUST:
  - normalize common NIRD encodings (e.g., Yes/No, 1/blank),
  - deduplicate facilities,
  - coerce burn bed fields,
  - and define facility classes that distinguish designation/capability flags from structural capacity fields.
- **FR-013**: Stage 01 (geography enrichment and denominators) MUST:
  - build a geographic backbone with stable keys (e.g., FIPS, county, tract),
  - join to denominator tables (e.g., total population, child population),
  - attach RUCA classifications,
  - and optionally overlay SVI or similar context layers.
  - use ACS 5-year 2022 denominators for total population and child population (under 18 years), use RUCA as the canonical rurality classification source, and treat SVI as an optional secondary overlay only.
- **FR-014**: Stage 02 (supply distribution and capacity baseline) MUST:
  - compute burn-center distribution,
  - derive normalized supply metrics (e.g., burn beds per population),
  - and produce the first Challenge Area 3 output focused on distribution and structural capacity.
- **FR-015**: Stage 03 (ground access burden) MUST:
  - estimate ground travel burden by tract/county/state,
  - summarize access by RUCA and state,
  - and generate outputs aligned with Challenge Area 3 example metrics on timely access.
- **FR-016**: Stage 04 (pediatric access gap) MUST:
  - define a pediatric population denominator,
  - compute pediatric-specific access metrics,
  - and treat pediatric access as a **distinct pillar** rather than a footnote.
- **FR-017**: Stage 05 (transfer-aware system access) MUST:
  - implement regionalized system logic (direct-to-definitive vs stabilize-and-transfer),
  - and model access in a way that can be compared to simple nearest-center baseline.
- **FR-018**: Stage 06 (structural capacity competition) MUST:
  - compute structural, not real-time, burn-bed accessibility and competition (e.g., E2SFCA-style logic internally),
  - and provide companion metrics that can be interpreted without exposing full technical details.
- **FR-019**: Stage 07 (air sensitivity scenario) MUST:
  - compare ground-only baseline to conditional ground-plus-air scenarios,
  - and clearly label all outputs as **scenario-based sensitivity**, not live operational truth.
- **FR-020**: Stage 08 (BEI composite hotspots and driver breakdown) MUST:
  - standardize pillars (supply, timely access, pediatric access, structural capacity),
  - compute a composite BEI from interpretable components,
  - define hotspot tiers and driver breakdown labels,
  - and keep need overlays (e.g., burden or vulnerability layers) separate from the core BEI.
- **FR-021**: Stage 09 (robustness and story exports) MUST:
  - perform robustness checks (e.g., weight and transfer-penalty sensitivity, ground vs transfer-aware vs air comparison, county vs tract aggregation),
  - produce polished, judge-facing figures,
  - generate one-line findings per figure/table,
  - and assemble final export bundles.

**Final output bundle**

- **FR-022**: The system MUST produce a **final output bundle** in `outputs/final_bundle/` containing at minimum:
  - `final_findings_summary.csv`,
  - `top_hotspots.csv`,
  - `figure_manifest.csv`,
  - `table_manifest.csv`,
  - `method_notes.md`,
  - a `deck_ready/` directory with polished PNGs,
  - a `map_ready/` directory with GeoJSON/Parquet layers,
  - a `metrics_ready/` directory with tidy tables suitable for frontend and slides.
- **FR-023**: Every final figure MUST have a **paired plain-language finding** stored in a machine-readable findings record and surfaced in the final findings summary.

**Validation and failure behavior**

- **FR-024**: The system MUST implement validations per stage such that **failed validations stop downstream execution**, return a clear non-zero status, and surface descriptive errors.
- **FR-025**: The command `results-pipeline validate` MUST run validations without recomputing all stages and provide a concise summary of pass/fail status per stage and per contract.
- **FR-026**: The command `results-pipeline list-stages` MUST enumerate all available stages, including IDs, questions, and brief descriptions, in DAG order.

**Methodological constraints and labeling**

- **FR-027**: No stage MAY make patient-level or real-time bed claims from NIRD; all capacity-related outputs MUST be clearly labeled as **structural** unless tied to an explicit scenario assumption.
- **FR-028**: All air transport-related outputs MUST be explicitly labeled as **sensitivity or scenario outputs**, not live operational truth.
- **FR-029**: Pediatric access metrics MUST remain clearly separated from adult access metrics in both intermediate outputs and final BEI construction.
- **FR-030**: Need overlays (e.g., burden, vulnerability, or incident layers) MUST NOT be directly mixed into the core BEI score; instead, they MUST be attached as separate overlays used for interpretation and prioritization.

**Stage contracts and notebook mapping**

- **FR-031**: Each stage MUST document:
  - which previous notebook(s) it replaces,
  - the judge-relevant question it answers,
  - and the export-ready outputs it produces, preserving the original notebook logic that each major stage answers one judge-relevant question.
- **FR-032**: The system MUST provide a **stage contract definition** (e.g., via `contracts/artifacts.py` and `contracts/schemas.py`) that can be used to validate required inputs and declared outputs at runtime.
- **FR-033**: The pipeline MUST define and enforce an **artifact naming convention** that allows downstream code and reviewers to locate and understand artifacts without inspecting notebook code.  
  - artifact naming MUST be stage-centric as the primary convention (e.g., `03_*`) with question-specific descriptors included in artifact names and manifest metadata.

**Phase-based development and scope**

- **FR-034**: The feature MUST support the phased implementation path described in the input (research/contracts, scaffolding, ingestion/validation, geography, challenge outputs, BEI/hotspots, exports, robustness) while remaining a **single feature** in Spec Kit, with phases reflected in `plan.md` and `tasks.md` rather than separate features.
- **FR-035**: For the hackathon MVP, the pipeline MUST be usable and judge-ready if only stages 00, 01, 02, 03, 04, 05, 08, and 09 are fully implemented and validated, with 06 and 07 additive but not required for base acceptance.  
  - subsets smaller than this MVP stage set (for example, 00–05 only) MAY be used for developer diagnostics but MUST NOT be treated as judge-ready accepted runs.

### Key Entities *(include if feature involves data)*

- **NIRD Facility**: Represents a facility record from the NIRD workbook, with structural designation and capability fields, structural capacity fields (e.g., TOTAL_BEDS, BURN_BEDS), identifiers, and facility class attributes derived in Stage 00.
- **Geographic Unit**: Represents a county, tract, or other spatial unit used for denominators and access metrics, keyed by stable geography identifiers (e.g., FIPS), with attributes such as total population, child population, RUCA classification, and optional SVI scores.
- **Scenario**: Represents a configuration of methodological assumptions (e.g., ground-only vs ground-plus-air, transfer penalties, weighting schemes) controlled via YAML config files and surfaced in outputs and findings.
- **Stage**: Represents an individual processing step in the pipeline (00–09) with a defined question, required inputs, declared outputs, validations, and a single `run(config)` entrypoint.
- **Artifact**: Represents a concrete output of a stage (dataset, table, figure, findings record) with a stable path, schema or structure, and associated metadata (e.g., stage_id, scenario, version).
- **Finding**: Represents a single machine-readable narrative statement about a result, following the findings schema (`stage_id`, `question`, `finding`, `why_it_matters`, `action_implication`) and designed for use in summaries, decks, and dashboards.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a configured environment with NIRD and augmentation sources available, running `results-pipeline run --config configs/mvp.yaml` MUST successfully produce a complete `outputs/final_bundle/` (including required manifests, findings, maps, metrics, and deck-ready figures) in a **single CLI invocation** without manual notebook interaction.
- **SC-002**: Each stage (00–09) MUST be runnable independently via `results-pipeline run-stage <stage_id> --config <config>` when its required inputs are present, and MUST emit all artifacts specified in its stage contract, with downstream stages failing gracefully if a required upstream artifact is missing or invalid.
- **SC-003**: All validations defined for stages 00–09 MUST either **pass** or, if they fail, MUST prevent downstream stages from executing and clearly report which validations failed and why.
- **SC-004**: For a reference input configuration, re-running the full pipeline with unchanged inputs MUST yield **stable schemas and file locations** (no missing or spurious outputs, no schema drift), enabling downstream automation and judge reproducibility.
- **SC-005**: For every final figure and key table in `outputs/final_bundle/`, there MUST be at least one corresponding **plain-language finding** in `final_findings_summary.csv` that explains the result, why it matters, and an action implication in non-technical terms.
- **SC-006**: Methodological constraints MUST be enforced such that:
  - no outputs claim patient-level or real-time capacity from NIRD,
  - structural capacity and air transport outputs are clearly labeled as such,
  - pediatric access metrics are reported separately from adult metrics,
  - and need overlays are attached as overlays rather than mixed into the BEI score.

## Assumptions

- The NIRD workbook and official documentation are available and can be treated as the **canonical source** for facility-level designation/capability and structural capacity fields.
- Approved public augmentation layers (e.g., Census, RUCA, SVI, routing/travel-time data) are accessible as local files under `data/` or via a pre-populated cache, and do not require the pipeline to manage external API quotas or credentials.
- A standard hackathon reference environment (e.g., local machine with sufficient memory and CPU) is used for performance expectations; extremely large-scale production deployments are **out of scope** for this feature.
- Judges and reviewers will primarily interact with outputs through the generated bundle (figures, tables, findings, manifests) rather than reading the code, so clarity and labeling in artifacts are prioritized over internal optimization details.
- The existing Challenge Area 3 notebooks are considered **source-of-truth product logic**, and any deviations in the pipeline must be explicitly documented in method notes and, if needed, back-ported to notebooks for consistency.
