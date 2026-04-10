# Quickstart: 004 Results Pipeline

## Prerequisites

- Python 3.11+ environment with project dependencies installed.
- NIRD input and approved public augmentation layers available under configured data paths.
- Config files present in `configs/`.

## 1) Validate Setup

From repository root:

```bash
python -m src.results_pipeline.cli list-stages
python -m src.results_pipeline.cli validate
```

Expected:

- Stage IDs `00` through `09` listed with question labels.
- Validation summary reports either pass status or actionable failures.

## 2) Run MVP Profile

```bash
python -m src.results_pipeline.cli run --config configs/mvp.yaml
```

MVP stages:

- `00, 01, 02, 03, 04, 05, 08, 09`

## 3) Run Full Profile

```bash
python -m src.results_pipeline.cli run --config configs/full.yaml
```

Full stages:

- `00` through `09` (includes `06` and `07`)

## 4) Rerun Individual Stages

Ground burden rerun:

```bash
python -m src.results_pipeline.cli run-stage 03 --config configs/default.yaml
```

Air sensitivity rerun:

```bash
python -m src.results_pipeline.cli run-stage 07 --config configs/scenarios/ground_plus_air.yaml
```

## 5) Build Final Exports

```bash
python -m src.results_pipeline.cli build-final-exports --config configs/default.yaml
```

Expected bundle root:

- `outputs/final_bundle/`

Required bundle members:

- `final_findings_summary.csv`
- `top_hotspots.csv`
- `figure_manifest.csv`
- `table_manifest.csv`
- `method_notes.md`
- `deck_ready/`
- `map_ready/`
- `metrics_ready/`

## 6) Contract and Quality Checks

- Each stage must produce at least one dataset, one table, one figure, and one findings record.
- Validation failures stop downstream execution.
- Air outputs must be labeled as scenario/sensitivity artifacts.
- Capacity outputs are labeled structural unless explicitly scenario-adjusted.
- Pediatric outputs remain separate from adult/general access outputs.

## 7) Troubleshooting

- If validation fails, run `validate` and inspect stage-level failure reasons before rerun.
- If a stage cannot run independently, check required upstream artifacts and config scenario compatibility.
- If final bundle is incomplete, rerun `build-final-exports` after confirming manifest-generation stage outputs.
