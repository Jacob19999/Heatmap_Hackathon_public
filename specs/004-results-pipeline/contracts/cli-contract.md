# CLI Contract: 004 Results Pipeline

## Command Surface

All commands are exposed via:

- `results-pipeline <command> [options]`
- `python -m src.results_pipeline.cli <command> [options]`

## Commands

### 1) `run`

Runs an orchestrated DAG profile.

**Input**

- `--config <path>` (required)

**Behavior**

- Determines profile and scenario from config.
- Executes stages in DAG order.
- Stops on first validation failure.

**Exit codes**

- `0`: success
- `2`: configuration or input contract error
- `3`: stage validation failure
- `4`: execution failure

### 2) `run-stage`

Runs one stage independently when dependencies are already satisfied.

**Input**

- `<stage_id>` (required)
- `--config <path>` (required)

**Behavior**

- Verifies required upstream artifacts exist and validate.
- Runs only requested stage and emits its artifacts and findings.

**Exit codes**

- `0`: success
- `2`: missing config or invalid stage ID
- `3`: missing/invalid upstream dependency
- `4`: stage execution failure

### 3) `validate`

Runs validation checks without requiring full recomputation.

**Input**

- `--config <path>` (optional; default config path if omitted)

**Behavior**

- Evaluates stage contracts and output contracts for selected profile.
- Prints pass/fail summary with failing checks.

**Exit codes**

- `0`: all checks pass
- `3`: one or more validation checks fail
- `4`: validation runtime error

### 4) `list-stages`

Lists stage metadata in DAG order.

**Input**

- none (optional `--config` allowed for profile filtering)

**Behavior**

- Outputs stage ID, question, and profile inclusion flags.

**Exit codes**

- `0`: success
- `4`: command failure

### 5) `build-final-exports`

Builds and validates final output bundle manifests and presentation artifacts.

**Input**

- `--config <path>` (required)

**Behavior**

- Assembles `outputs/final_bundle/` required files and directories.
- Verifies each final figure has a corresponding findings entry.

**Exit codes**

- `0`: success
- `3`: missing required export artifact(s)
- `4`: export assembly failure

## Global Contract Rules

- Validation failures are blocking; no best-effort continuation in orchestrated runs.
- Scenario labels must be propagated to scenario-sensitive outputs.
- Structural capacity and air-sensitivity honesty labels are mandatory in findings/method notes.
- Commands are deterministic with stable input data and identical config.
