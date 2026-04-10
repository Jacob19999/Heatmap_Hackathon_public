# Implementation Plan: 004 Results Pipeline

**Branch:** `004-results-pipeline`  
**Date:** 2026-03-16  
**Spec:** `specs/004-results-pipeline/spec.md`

## Summary

Build a reproducible Python analytics pipeline that replaces the existing Challenge Area 3 notebook execution path with a staged, contract-driven CLI workflow. The pipeline must regenerate all required Challenge Area 3 outputs from configured NIRD inputs and approved public augmentation layers, while preserving the original notebook logic that each major stage answers one judge-relevant question.

The pipeline will support two official run profiles:

- **MVP profile:** stages `00, 01, 02, 03, 04, 05, 08, 09`
- **Full profile:** stages `00–09`, including `06` structural capacity competition and `07` air sensitivity

The system will enforce stage validation gates, stable artifact naming, scenario labeling, and final export bundling into a judge-ready results package containing figures, tables, maps, findings, manifests, and method notes.

This feature is a **single Spec Kit feature** implemented in phases. Phases exist in `plan.md` and `tasks.md`; they are not separate features.

---

## Scope Lock

This plan is explicitly scoped to **Challenge Area 3: Equitable Access to Burn Care**.

The pipeline must remain aligned to these non-negotiable rules:

- NIRD is treated as **hospital-level structural infrastructure data**, not patient-level clinical data.
- The pipeline must generate the four core challenge outputs:
  - burn-center distribution
  - rural vs urban travel burden
  - pediatric access relative to child population
  - burn-bed structural capacity
- BEI is a **transparent composite built after interpretable companion metrics exist**
- need overlays remain **separate from the BEI core score**
- air transport outputs are **scenario/sensitivity layers only**
- the MVP accepted run is **00, 01, 02, 03, 04, 05, 08, 09**
- smaller subsets may be used for development/debugging but are **not judge-ready accepted runs**

---

## Technical Context

### Language and runtime

- **Python:** 3.11+

### Core dependencies

Use a deliberately conservative core stack for stability and reproducibility:

- `pandas`
- `numpy`
- `geopandas`
- `shapely`
- `pyarrow`
- `matplotlib`
- `pydantic`
- `typer`
- `requests`
- `openpyxl`
- `pyyaml`
- `networkx` only if required for routing utilities

### Optional dependencies

These are allowed only when justified by a specific stage or analysis need, and must not be required for MVP acceptance:

- `scikit-learn`
- `scipy`
- `plotly`
- `contextily`
- `folium`
- `tqdm`

### Explicitly de-prioritized

These should not be assumed in the initial MVP implementation unless later justified by research/design artifacts:

- `hdbscan`
- `esda`
- `libpysal`
- `seaborn`
- `cenpy`

### Storage model

File-based artifact pipeline:

- source inputs under `data/raw/`
- intermediate stage outputs under `data/interim/`
- final processed stage outputs under `data/processed/`
- stage exports under `outputs/figures/`, `outputs/tables/`, `outputs/metrics/`
- judge bundle under `outputs/final_bundle/`

### Execution model

- local CLI-driven batch execution
- deterministic reruns from config
- stage-level reruns without recomputing the entire pipeline
- cache-aware for expensive travel-time or scenario computations

### Testing and quality

- `pytest`
- `ruff`
- contract tests for stage interfaces and artifact manifests
- schema validation tests for findings and manifest outputs

---

## Constitution Check

### Pre-Research Gate

**Primary use case lock:**  
Pipeline is fully centered on equitable access to burn care as the single first-class use case.  
**PASS**

**Structural-access truthfulness:**  
Capacity and access outputs are explicitly structural or scenario-based. No patient-level or real-time claims are permitted.  
**PASS**

**Challenge-output alignment:**  
Stage mapping covers distribution, rural/urban burden, pediatric access, structural capacity, transfer-aware access, and air sensitivity.  
**PASS**

**Composite transparency:**  
BEI remains decomposable into interpretable pillars, with need overlays attached separately.  
**PASS**

**Delivery sequence:**  
Pipeline/data products are implemented before any frontend/deck integration concerns.  
**PASS**

No constitution violations at planning start.

---

## Project Structure

### Feature documentation

```text
specs/004-results-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── stage-findings.schema.json
│   ├── artifact-manifest.schema.json
│   ├── stage-contract.schema.json
│   └── cli-contract.md
└── tasks.md
```

### Source code

```text
src/
├── results_pipeline/
│   ├── __init__.py
│   ├── cli.py
│   ├── settings.py
│   ├── logging.py
│   ├── registry.py
│   ├── orchestrator.py
│   ├── contracts/
│   │   ├── artifacts.py
│   │   ├── schemas.py
│   │   └── stage.py
│   ├── io/
│   │   ├── loaders.py
│   │   ├── writers.py
│   │   └── cache.py
│   ├── utils/
│   │   ├── paths.py
│   │   ├── plotting.py
│   │   ├── validation.py
│   │   ├── geography.py
│   │   ├── routing.py
│   │   └── normalization.py
│   └── stages/
│       ├── stage_00_data_audit.py
│       ├── stage_01_geography_enrichment.py
│       ├── stage_02_supply_capacity_baseline.py
│       ├── stage_03_ground_access_burden.py
│       ├── stage_04_pediatric_access_gap.py
│       ├── stage_05_transfer_aware_access.py
│       ├── stage_06_structural_capacity.py
│       ├── stage_07_air_sensitivity.py
│       ├── stage_08_bei_hotspots.py
│       └── stage_09_story_exports.py

configs/
├── default.yaml
├── mvp.yaml
├── full.yaml
└── scenarios/
    ├── ground_only.yaml
    └── ground_plus_air.yaml

data/
├── raw/
├── interim/
└── processed/

outputs/
├── figures/
├── tables/
├── metrics/
└── final_bundle/

tests/
├── unit/
├── integration/
└── contract/
```

### Structure decision

Use a single Python repository with a new package under `src/results_pipeline/`. Existing notebook logic remains the analytical source during migration, but the shipped feature is the package + CLI, not notebook execution.

---

## Architecture Decisions

### 1) Orchestration model

Use a lightweight internal DAG orchestrator rather than a heavy external workflow system.

Canonical DAG:

```text
00 -> 01 -> 02 -> 03 -> 04 -> 05 -> 08 -> 09
                  \-> 06 -/
                  \-> 07 -/
```

Notes:

- `06` and `07` are additive for full runs
- `08` must tolerate MVP mode where `06` and `07` are absent
- `09` assembles final bundle from whichever stages are active under the run profile

### 2) Stage contract model

Every stage must implement a common interface with:

- `stage_id`
- `name`
- `question`
- `description`
- `replaces_notebooks`
- `required_inputs`
- `produced_datasets`
- `produced_tables`
- `produced_figures`
- `produced_findings`
- `validations`
- `run(config)`

This adds `name`, `description`, and `replaces_notebooks` to improve auditability and support `list-stages`.

### 3) Config layering

Adopt layered config resolution:

1. `configs/default.yaml` for shared defaults
2. `configs/mvp.yaml` or `configs/full.yaml` for run profile
3. optional scenario overlay from `configs/scenarios/*.yaml`

Merged config precedence:

`default < profile < scenario < CLI overrides`

This keeps scenario handling explicit and deterministic.

### 4) Artifact naming convention

Use stage-centric artifact naming as the primary rule:

- datasets: `03_ground_access_metrics.parquet`
- tables: `03_population_coverage_thresholds.csv`
- figures: `03_rural_urban_travel_boxplot.png`
- findings: `03_findings.json`

All artifacts must also appear in a manifest with:

- stage ID
- question
- scenario label
- artifact type
- path
- schema/version metadata

### 5) Manifest-first outputs

Every stage writes:

- artifacts
- stage manifest
- machine-readable findings

The final bundle is built from manifests, not ad hoc file discovery. This reduces ambiguity and improves traceability.

---

## Implementation Strategy

## Phase 0 — Research and decision locking

### Objectives

Resolve the few remaining planning decisions before code architecture is finalized.

### Decisions to lock

- denominator vintages and sources
- rurality classification source
- optional context layers
- stage naming and manifest metadata
- supported run profiles
- minimal deterministic rerun guarantees
- cache behavior for travel-time/scenario outputs

### Locked decisions for this feature

These should be treated as resolved in `research.md` unless new evidence forces revision:

- **Total population denominator:** ACS 5-year 2022
- **Child population denominator:** ACS 5-year 2022, under 18
- **Rurality source:** RUCA
- **SVI:** optional overlay only, not BEI core
- **MVP accepted run:** `00, 01, 02, 03, 04, 05, 08, 09`
- **Artifact naming:** stage-centric with descriptive suffix
- **Air transport:** scenario-only sensitivity layer
- **Structural capacity:** explicitly structural, not live operational truth

### Deliverables

- `research.md`
- locked decision log
- dependency justification notes
- final config layering decision

### Exit criteria

- no unresolved methodological blockers remain for architecture design
- all required spec ambiguities are either locked or explicitly deferred

---

## Phase 1 — Design and contracts

### Objectives

Translate the feature spec into explicit runtime contracts and schemas.

### Deliverables

- `data-model.md`
- `contracts/stage-findings.schema.json`
- `contracts/artifact-manifest.schema.json`
- `contracts/stage-contract.schema.json`
- `contracts/cli-contract.md`
- `quickstart.md`

### Required design content

`data-model.md` must define:

- NIRD Facility
- Geographic Unit
- Scenario
- Stage
- Artifact
- Finding

`stage-findings.schema.json` must enforce:

- `stage_id`
- `question`
- `finding`
- `why_it_matters`
- `action_implication`
- optional scenario metadata

`artifact-manifest.schema.json` must enforce:

- artifact type
- stage ID
- scenario label
- path
- version/schema
- checksum or file metadata where feasible

`cli-contract.md` must define:

- commands
- arguments/options
- expected exit codes
- validation failure behavior
- profile/scenario handling
- non-zero failure policy

### Exit criteria

- stage and artifact contracts are sufficiently concrete to generate implementation tasks
- design remains constitution-compliant

---

## Phase 2 — Scaffolding and orchestration core

### Objectives

Build the package foundation and CLI/runtime skeleton.

### Deliverables

- package skeleton under `src/results_pipeline/`
- `cli.py`
- `settings.py`
- `registry.py`
- `orchestrator.py`
- logging utilities
- path utilities
- config loading and merging
- stage registration system

### Key implementation rules

- no hard-coded absolute paths
- no notebook execution dependency
- no direct file discovery outside declared contracts
- all stage execution goes through registry/orchestrator
- config must be validated before execution begins

### Exit criteria

- `results-pipeline list-stages` works
- `results-pipeline validate` can inspect declared contracts
- orchestrator can resolve DAG order from stage registry

---

## Phase 3 — Ingestion, normalization, and validation core

### Objectives

Implement source loading, normalization, and runtime validation plumbing.

### Deliverables

- `io/loaders.py`
- `io/writers.py`
- `io/cache.py`
- `utils/validation.py`
- `utils/normalization.py`
- Stage 00 implementation
- stage manifest writing
- findings writing
- artifact existence/schema validation

### Stage 00 must cover

- NIRD workbook loading
- worksheet presence checks
- column presence checks
- normalization of common Yes/No and 1/blank encodings
- bed field coercion
- deduplication policy
- facility class derivation
- data quality summary exports

### Exit criteria

- Stage 00 runs independently
- Stage 00 emits valid datasets/tables/figures/findings
- validation failure stops downstream execution cleanly

---

## Phase 4 — Geographic backbone

### Objectives

Build the reusable denominator and geography layer required by downstream stages.

### Deliverables

- Stage 01 implementation
- geography utilities
- denominator loaders/join logic
- stable geographic unit outputs

### Stage 01 must cover

- FIPS assignment
- county/tract geographic keys
- facility geographic enrichment
- total population joins
- child population joins
- RUCA assignment
- optional SVI overlay
- reusable county and tract denominator tables

### Exit criteria

- Stage 01 outputs are sufficient for 02–09
- geography joins are validated for key completeness
- missing geography errors are descriptive and actionable

---

## Phase 5 — Core challenge outputs (MVP)

### Objectives

Implement the MVP stages that produce the required Challenge Area 3 story.

### Deliverables

- Stage 02 implementation
- Stage 03 implementation
- Stage 04 implementation
- Stage 05 implementation
- Stage 08 implementation
- Stage 09 implementation

### Mandatory MVP outcome

A successful run of:

```bash
results-pipeline run --config configs/mvp.yaml
```

must produce a complete judge-ready bundle.

### Stage requirements

- **02** — supply distribution and structural capacity baseline
- **03** — ground travel burden by tract/county/state, summarized by RUCA/state
- **04** — pediatric-specific access metrics and pediatric gap outputs
- **05** — direct vs transfer-aware access comparison
- **08** — interpretable BEI with separate need overlays
- **09** — robustness, final story exports, bundle assembly

### Exit criteria

- all MVP stages pass contract tests
- final bundle exists and is internally traceable through manifests
- each final figure/table has at least one plain-language finding

---

## Phase 6 — Additive full-run stages

### Objectives

Implement the two non-MVP but high-value analytic extensions.

### Deliverables

- Stage 06 implementation
- Stage 07 implementation
- `configs/full.yaml`
- scenario-specific config tests

### Stage 06

Structural capacity competition:

- structural, not live, accessibility logic
- interpretable companion outputs
- clear labeling of technical vs presentation metrics

### Stage 07

Air sensitivity:

- ground-only vs conditional ground-plus-air
- explicit scenario labeling
- no modification of primary ground-only artifacts

### Exit criteria

- full run succeeds
- scenario labels propagate into manifests, findings, and filenames where appropriate
- `08` and `09` correctly consume additive outputs when present

---

## Phase 7 — Final exports, reproducibility, and robustness

### Objectives

Harden the bundle, validation, and rerun experience for judges and reviewers.

### Deliverables

- final bundle assembly logic
- figure/table manifests
- `method_notes.md`
- `final_findings_summary.csv`
- robustness outputs
- deterministic rerun checks
- documentation of scenario assumptions and caveats

### Required final bundle

`outputs/final_bundle/` must contain at minimum:

- `final_findings_summary.csv`
- `top_hotspots.csv`
- `figure_manifest.csv`
- `table_manifest.csv`
- `method_notes.md`
- `deck_ready/`
- `map_ready/`
- `metrics_ready/`

### Exit criteria

- rerunning unchanged inputs yields stable paths and schemas
- reviewer can trace each final artifact back to stage, question, and finding
- validate/build-final-exports behavior is documented and testable

---

## Validation and Failure Policy

Validation must be treated as a first-class pipeline behavior, not an afterthought.

### Rules

- every stage declares validations
- failed validations block downstream stages
- failures return non-zero exit codes
- errors must identify:
  - stage
  - failed contract or validation
  - missing or invalid artifact
  - suggested remediation when possible

### Validation categories

- input existence
- required columns/fields
- schema conformance
- row/key uniqueness where required
- expected artifact creation
- scenario consistency
- manifest completeness

### Command behavior

- `results-pipeline validate` inspects readiness/contracts without forcing full recomputation
- `results-pipeline run` validates before execution and between stages
- `results-pipeline build-final-exports` refuses to run if required upstream artifacts are invalid

---

## Testing Strategy

### Unit tests

- config loading/merging
- path building
- manifest generation
- finding schema validation
- stage registration

### Contract tests

- each stage exposes required interface fields
- each stage declares outputs in valid format
- findings and artifact manifests match schemas
- stage-specific output naming follows convention

### Integration tests

- MVP DAG execution
- independent stage rerun
- validation stop-on-fail
- final bundle assembly
- scenario labeling behavior for stage 07

### Reproducibility tests

- rerun with unchanged inputs produces same paths and schemas
- no spurious missing outputs
- manifests remain stable except for allowed metadata fields

---

## Migration Strategy

The notebooks remain the source analytical reference during migration, but the package becomes the operational path.

### Rules

- stage modules must document which notebook(s) they replace
- deviations from notebook logic must be recorded in `method_notes.md`
- pipeline outputs, not notebooks, become the judge-facing source of truth once validated

This reduces the risk of silent divergence while still allowing iterative migration.

---

## Risks and Mitigations

### Risk: dependency bloat slows implementation

**Mitigation:** keep MVP core stack minimal; treat advanced spatial/statistical packages as optional.

### Risk: travel-time stages become brittle or slow

**Mitigation:** formalize cache behavior early; allow precomputed matrices; make routing source configurable.

### Risk: scenario outputs contaminate baseline outputs

**Mitigation:** enforce scenario labels in manifests, filenames, and findings; prohibit overwrite of baseline artifacts.

### Risk: Stage 08 becomes over-coupled to optional stages

**Mitigation:** design 08 to support MVP pillar set and incorporate 06/07 only when present.

### Risk: notebooks and pipeline drift apart

**Mitigation:** document notebook replacement mapping and record methodological deviations in method notes.

---

## Post-Design Constitution Check

**Scope integrity:**  
Feature remains anchored to Challenge Area 3 structural equity outputs only.  
**PASS**

**Truthfulness policy:**  
Contracts and findings require structural/scenario labeling and prohibit patient-level or operational claims.  
**PASS**

**Challenge-output coverage:**  
MVP/full profiles cover required challenge outputs.  
**PASS**

**Composite transparency:**  
BEI remains decomposable and overlay-aware.  
**PASS**

**Quality standards:**  
Contracts and manifests carry assumptions, provenance, and traceability metadata.  
**PASS**

No constitution violations introduced by this refined plan.

---

## Complexity Tracking

No exceptional complexity waiver is required at this stage.

The main complexity risk is not conceptual scope, but implementation discipline:

- keeping contracts strict,
- keeping dependencies lean,
- and preventing optional stages from destabilizing MVP acceptance.

---

## What I changed from your version

Key refinements relative to the initial plan:

- reduced dependency sprawl and clarified “core vs optional vs de-prioritized”
- added `registry.py`, `orchestrator.py`, and `stage-contract.schema.json` explicitly
- made config layering concrete and deterministic
- added exit criteria per phase
- separated MVP acceptance from additive full-run work
- made validation and failure behavior more explicit
- clarified notebook-to-pipeline migration strategy
- strengthened artifact/manifest traceability and testing strategy

This plan is now tightly aligned with the spec, constitution, and Spec Kit flow, and is ready to be translated directly into `tasks.md`.

