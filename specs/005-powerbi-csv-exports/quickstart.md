# Quickstart: Phase 7 Final Exports

## Prerequisites

- Python 3.11+ environment with project dependencies installed.
- Existing challenge outputs already present under `Data/output/`.
- Filled processed travel matrices present under `Data/output/Travel Dist Processed/`:
  - `usa_low_detail_county_county_travel_time_matrix_filled.parquet`
  - `valhalla_mn_hospitals_timedist_filled.parquet`
- Existing manifests, tables, and figures available from prior pipeline runs.

## 1) Validate current export prerequisites

From repository root:

```bash
python -m src.results_pipeline.cli validate --config configs/default.yaml
```

Expected checks:

- required source tables exist under `Data/output/tables/`
- required manifests exist under `Data/output/manifests/`
- filled travel matrices are present under `Data/output/Travel Dist Processed/`
- scenario labels and source profile references are valid

## 2) Build the final CSV bundle

```bash
python -m src.results_pipeline.cli build-final-exports --config configs/default.yaml
```

Expected bundle root:

- `Data/output/final_bundle/`

Required outputs:

- `final_findings_summary.csv`
- `top_hotspots.csv`
- `figure_manifest.csv`
- `table_manifest.csv`
- one or more report-ingestion metric CSVs
- one or more map-join CSVs
- one or more robustness comparison CSVs
- `method_notes.md`
- bundle manifest JSON

## 3) Review the report-ingestion pack

Confirm that:

- every CSV has stable business-facing column names
- each CSV has a documented row grain
- baseline and sensitivity outputs are labeled distinctly
- every report-driving artifact is covered by findings and manifest rows

## 4) Re-run for reproducibility

Run the same command again with unchanged inputs:

```bash
python -m src.results_pipeline.cli build-final-exports --config configs/default.yaml
python -m src.results_pipeline.cli validate --config configs/default.yaml
```

Expected outcome:

- identical final file set
- identical CSV schemas and row grain
- reproducibility metadata indicates a stable rerun

## 5) Troubleshooting

- If validation fails on missing travel matrices, confirm the processed files are in `Data/output/Travel Dist Processed/` and not only in `Data/output/tables/`.
- If required CSVs are missing, inspect the bundle manifest and source manifests to find the missing result area.
- If scenario labels drift, verify that baseline and `ground_plus_air` outputs are exported separately.
- If traceability fails, confirm each final artifact is linked to a findings row and manifest record.
