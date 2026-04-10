from __future__ import annotations

from pathlib import Path
from typing import Any

from .logging import log_pipeline_failure, log_stage_end, log_stage_start
from .registry import create_default_registry
from .settings import RuntimeConfig
from .stages import stage_00_data_audit
from .stages import stage_01_geography_enrichment
from .stages import stage_02_supply_capacity_baseline
from .stages import stage_03_ground_access_burden
from .stages import stage_04_pediatric_access_gap
from .stages import stage_05_transfer_aware_access
from .stages import stage_06_structural_capacity
from .stages import stage_07_air_sensitivity
from .stages import stage_08_bei_hotspots
from .stages import stage_09_story_exports


def _run_stage_impl(stage_id: str, config: RuntimeConfig) -> dict[str, Any]:
    if stage_id == "00":
        return stage_00_data_audit.run(config)
    if stage_id == "01":
        return stage_01_geography_enrichment.run(config)
    if stage_id == "02":
        return stage_02_supply_capacity_baseline.run(config)
    if stage_id == "03":
        return stage_03_ground_access_burden.run(config)
    if stage_id == "04":
        return stage_04_pediatric_access_gap.run(config)
    if stage_id == "05":
        return stage_05_transfer_aware_access.run(config)
    if stage_id == "06":
        return stage_06_structural_capacity.run(config)
    if stage_id == "07":
        return stage_07_air_sensitivity.run(config)
    if stage_id == "08":
        return stage_08_bei_hotspots.run(config)
    if stage_id == "09":
        return stage_09_story_exports.run(config)
    return {"ok": True, "stage_id": stage_id, "status": "stub"}


def plan_for_profile(config: RuntimeConfig) -> list[str]:
    registry = create_default_registry()
    if config.stages:
        return config.stages
    if config.profile == "full":
        return ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"]
    if config.profile == "stage":
        return []
    return ["00", "01", "02", "03", "04", "05", "08", "09"]


def _validate_dependencies(stage_ids: list[str]) -> list[str]:
    registry = create_default_registry()
    missing: list[str] = []
    selected = set(stage_ids)
    for sid in stage_ids:
        for dep in registry.deps.get(sid, []):
            if dep not in selected:
                missing.append(f"{sid} missing dependency {dep}")
    return missing


def _validate_summary(profile: str, stage_ids: list[str], errors: list[str]) -> dict[str, Any]:
    return {
        "ok": len(errors) == 0,
        "profile": profile,
        "stages": stage_ids,
        "errors": errors,
        "summary": {
            "status": "PASS" if len(errors) == 0 else "FAIL",
            "checked_stages": len(stage_ids),
            "error_count": len(errors),
        },
    }


def _diagnose_final_export_inputs(config: RuntimeConfig) -> list[str]:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    outputs = config.raw.get("outputs", {})
    figures_dir = Path(outputs.get("figures_dir", root / "outputs" / "figures"))
    tables_dir = Path(outputs.get("tables_dir", root / "outputs" / "tables"))
    metrics_dir = Path(outputs.get("metrics_dir", root / "outputs" / "metrics"))
    missing: list[str] = []
    if not figures_dir.exists():
        missing.append(f"Missing figures directory: {figures_dir}")
    elif not any(figures_dir.glob("*.png")):
        missing.append(f"No figure artifacts found in: {figures_dir}")
    if not tables_dir.exists():
        missing.append(f"Missing tables directory: {tables_dir}")
    elif not any(tables_dir.glob("*.csv")):
        missing.append(f"No table artifacts found in: {tables_dir}")
    if not metrics_dir.exists():
        missing.append(f"Missing metrics directory: {metrics_dir}")
    elif not any(metrics_dir.glob("*_findings_*.json")):
        missing.append(f"No findings artifacts found in: {metrics_dir}")
    return missing


def run_pipeline(config: RuntimeConfig) -> dict[str, Any]:
    stage_ids = plan_for_profile(config)
    errors = _validate_dependencies(stage_ids)
    if errors:
        summary = _validate_summary(config.profile, stage_ids, errors)
        log_pipeline_failure(summary)
        return summary
    results: list[dict[str, Any]] = []
    for sid in stage_ids:
        log_stage_start(sid, {"profile": config.profile})
        try:
            result = _run_stage_impl(sid, config)
        except Exception as exc:  # noqa: BLE001 - converted to structured pipeline failure
            log_stage_end(sid, {"status": "failed", "errors": [str(exc)]})
            summary = {
                "ok": False,
                "profile": config.profile,
                "stages": stage_ids,
                "failed_stage": sid,
                "errors": [str(exc)],
            }
            log_pipeline_failure(summary)
            return summary
        if not result.get("ok", False):
            log_stage_end(sid, {"status": "failed", "errors": result.get("errors", [])})
            summary = {"ok": False, "profile": config.profile, "stages": stage_ids, "failed_stage": sid, "result": result}
            log_pipeline_failure(summary)
            return summary
        log_stage_end(sid, {"status": result.get("status", "ok")})
        results.append(result)
    return {"ok": True, "profile": config.profile, "stages": stage_ids, "results": results}


def run_single_stage(config: RuntimeConfig, stage_id: str) -> dict[str, Any]:
    registry = create_default_registry()
    if stage_id not in registry.stages:
        return {"ok": False, "errors": [f"Unknown stage '{stage_id}'"]}
    log_stage_start(stage_id, {"mode": "run-stage"})
    try:
        result = _run_stage_impl(stage_id, config)
    except Exception as exc:  # noqa: BLE001
        log_stage_end(stage_id, {"status": "failed", "errors": [str(exc)]})
        return {"ok": False, "stage_id": stage_id, "errors": [str(exc)]}
    log_stage_end(stage_id, {"status": result.get("status", "ok") if result.get("ok", False) else "failed"})
    return result


def validate_pipeline(config: RuntimeConfig) -> dict[str, Any]:
    stage_ids = plan_for_profile(config)
    errors = _validate_dependencies(stage_ids)
    return _validate_summary(config.profile, stage_ids, errors)


def build_final_exports(config: RuntimeConfig) -> dict[str, Any]:
    missing = _diagnose_final_export_inputs(config)
    if missing:
        return {
            "ok": False,
            "stage_id": "09",
            "errors": [
                "Cannot build final exports because upstream artifacts are missing.",
                *missing,
            ],
        }
    # Stage 09 assembles the final bundle; run it if not already in plan.
    result = run_single_stage(config, "09")
    return result
