# Implementation Plan: Phase 7 Final Exports

**Branch**: `005-powerbi-csv-exports` | **Date**: 2026-03-16 | **Spec**: `C:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon\specs\005-powerbi-csv-exports\spec.md`  
**Input**: Feature specification from `C:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon\specs\005-powerbi-csv-exports\spec.md`

## Summary

Implement a deterministic final-export layer that turns the existing challenge artifacts under `Data/output/` into a complete Power BI ingestion bundle of CSVs, manifests, findings summaries, and robustness tables. The plan uses the current `src/pipeline/` export/manifests code and `Data/output/` path conventions as the implementation base, while exposing the finalized workflow through the `src/results_pipeline/cli.py` command surface so final exports, validation, and reproducibility checks follow the broader pipeline contract.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pandas, geopandas, pyarrow/parquet IO, typer CLI, json/jsonschema-style contract validation, existing project analytics stack from the workspace rules  
**Storage**: File-based artifacts under `Data/` using Parquet, GeoJSON, JSON, CSV, Markdown, and Excel inputs  
**Testing**: `pytest`, targeted contract/integration tests under `src/tests/`, `ruff check .` for Python hygiene  
**Target Platform**: Local Python analytics workflow on Windows with file-based outputs and reproducible reruns  
**Project Type**: Python analytics CLI and export pipeline  
**Performance Goals**: Build the final CSV/report bundle from already-produced artifacts without recomputing routing or BEI stages; validation should complete against existing artifacts in minutes and reruns with unchanged inputs should keep identical file sets and schemas  
**Constraints**: Must preserve Constitution truthfulness around structural access, capacity, and scenario labeling; must not require AI inspection of the restricted full NIRD workbook; must use real repository paths under `Data/output/`; must support handoff to Power BI without manual reshaping; must surface failures for missing or inconsistent export artifacts  
**Scale/Scope**: Phase 7 focuses on the existing Minnesota high-detail and USA low-detail county outputs, the filled travel-distance matrices in `Data/output/Travel Dist Processed/`, current manifests/figures/tables, and the report-ingestion bundle plus reproducibility evidence for judge-ready delivery

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Mission alignment**: Pass. The feature serves Challenge Area 3 by packaging structural burn-care access outputs for final reporting rather than expanding into a new product area.
- **Primary use-case lock**: Pass. The bundle is explicitly for equitable access to burn care reporting and does not introduce referral-network or telemedicine workflows as peer products.
- **Structural-access truthfulness**: Pass. The plan requires structural-capacity labeling, scenario-specific air labels, and method notes that repeat the model limits.
- **Challenge-output alignment**: Pass. Final exports are constrained to challenge outputs, supporting findings, and robustness comparisons tied to distribution, travel burden, pediatric access, capacity, and scenario sensitivity.
- **Composite transparency**: Pass. Final bundle contracts include component-level outputs, findings, and traceability rather than exporting only a bare BEI score.
- **Data governance**: Pass. The implementation consumes existing derived artifacts and manifests, not direct AI inspection of the restricted full NIRD source file.
- **Gate status before research**: Pass. No constitutional violations require exception handling.
- **Gate status after Phase 1 design**: Pass. The designed contracts preserve scenario honesty, structural-capacity framing, and clear lineage from exported CSVs back to result areas and findings.

## Project Structure

### Documentation (this feature)

```text
specs/005-powerbi-csv-exports/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── final-export-cli.md
│   └── powerbi-bundle-manifest.schema.json
└── tasks.md
```

### Source Code (repository root)

```text
Data/
└── output/
    ├── Travel Dist Processed/
    ├── figures/
    ├── geojson/
    ├── manifests/
    ├── tables/
    └── final_bundle/

src/
├── pipeline/
│   ├── config.py
│   ├── export.py
│   ├── presentation_scope.py
│   ├── run_dual_path_pipeline.py
│   └── sanity_check.py
├── results_pipeline/
│   ├── __init__.py
│   └── cli.py
└── tests/
    ├── test_air_sensitivity.py
    ├── test_direct_outputs.py
    ├── test_export_contracts.py
    └── test_sanity.py
```

**Structure Decision**: Use the existing single Python project structure already present in the repository. Phase 7 implementation should build on `src/pipeline/` and `Data/output/` because those paths already contain the real artifacts, manifests, and naming conventions. `src/results_pipeline/cli.py` remains the external command surface for final export and validation behavior, but the plan deliberately avoids a full architecture migration before the CSV export pack is working and reproducible.

## Phase 0 Research Focus

1. Confirm the canonical final bundle root and export path policy using the repository’s current `Data/output/` layout.
2. Confirm the authoritative processed travel-matrix inputs for reproducibility and validation, incorporating the filled Parquet files now present in `Data/output/Travel Dist Processed/`.
3. Define the CSV bundle contract for Power BI ingestion, including manifests, findings, traceability, and robustness outputs.
4. Define the reproducibility strategy for stable reruns, including which metadata can vary and which schemas/paths must not drift.
5. Define how the stub `results_pipeline` CLI should wrap or call the existing `src/pipeline/` export code during this phase.

## Phase 1 Design Scope

1. Model the final bundle entities, manifest rows, findings rows, robustness outputs, and reproducibility records.
2. Define CLI behavior for `build-final-exports` and `validate` with Phase 7-specific failure conditions and exit codes.
3. Define the schema for the Power BI bundle manifest and CSV inventory so downstream consumers can trust bundle completeness.
4. Document a quickstart that starts from existing `Data/output/` artifacts rather than assuming the full stage-based pipeline is already implemented.
5. Update agent context so the workspace guidance reflects the Phase 7 export-pack and reproducibility focus.

## Complexity Tracking

No constitution violations or exceptional complexity waivers are currently required.
