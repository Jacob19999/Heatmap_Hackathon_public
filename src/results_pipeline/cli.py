from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .orchestrator import (
    build_final_exports,
    plan_for_profile,
    run_pipeline,
    run_single_stage,
    validate_pipeline,
)
from .registry import create_default_registry
from .settings import load_runtime_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="results-pipeline")
    parser.add_argument("--version", action="store_true", help="Show version and exit.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-stages", help="List registered stages in DAG order.")

    run_p = sub.add_parser("run", help="Run orchestrated pipeline profile.")
    run_p.add_argument("--config", required=True, type=Path, help="Path to config YAML.")
    run_p.add_argument("--scenario", type=Path, default=None, help="Optional path to scenario YAML (e.g. configs/scenarios/ground_plus_air.yaml).")

    run_s = sub.add_parser("run-stage", help="Run a single stage.")
    run_s.add_argument("stage_id", help="Stage identifier, e.g. 03")
    run_s.add_argument("--config", required=True, type=Path, help="Path to config YAML.")
    run_s.add_argument("--scenario", type=Path, default=None, help="Optional path to scenario YAML.")

    val_p = sub.add_parser("validate", help="Validate pipeline contracts and configuration.")
    val_p.add_argument("--config", required=False, type=Path, help="Path to config YAML.")

    exp_p = sub.add_parser("build-final-exports", help="Build final output bundle.")
    exp_p.add_argument("--config", required=True, type=Path, help="Path to config YAML.")

    return parser


def _print_stages() -> int:
    registry = create_default_registry()
    ordered = registry.ordered_stage_ids()
    for stage_id in ordered:
        stage = registry.get(stage_id)
        print(f"{stage.stage_id}\t{stage.name}\t{stage.question}\t{stage.description}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "list-stages":
        return _print_stages()

    if args.command == "run":
        config = load_runtime_config(args.config, scenario_path=args.scenario)
        summary = run_pipeline(config=config)
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("ok", False) else 4

    if args.command == "run-stage":
        config = load_runtime_config(args.config, scenario_path=args.scenario)
        summary = run_single_stage(config=config, stage_id=args.stage_id)
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("ok", False) else 4

    if args.command == "validate":
        config = load_runtime_config(args.config) if args.config else load_runtime_config(Path("configs/default.yaml"))
        summary = validate_pipeline(config=config)
        status = summary.get("summary", {}).get("status", "PASS" if summary.get("ok", False) else "FAIL")
        checked = summary.get("summary", {}).get("checked_stages", len(summary.get("stages", [])))
        error_count = summary.get("summary", {}).get("error_count", len(summary.get("errors", [])))
        print(f"VALIDATION {status} | stages={checked} | errors={error_count}")
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("ok", False) else 3

    if args.command == "build-final-exports":
        config = load_runtime_config(args.config)
        summary = build_final_exports(config=config)
        status = "PASS" if summary.get("ok", False) else "FAIL"
        print(f"BUILD-FINAL-EXPORTS {status}")
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("ok", False) else 3

    return 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

