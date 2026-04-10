from __future__ import annotations

from typing import Any

ARTIFACT_FORMAT_RULES: dict[str, set[str]] = {
    "dataset": {"parquet", "csv", "geojson", "md"},
    "table": {"csv"},
    "figure": {"png", "pdf"},
    "finding": {"json"},
    "manifest": {"json"},
}


def require_fields(payload: dict[str, Any], fields: list[str]) -> list[str]:
    missing: list[str] = []
    for field in fields:
        if field not in payload:
            missing.append(field)
    return missing


def validate_finding_payload(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    required = ["stage_id", "question", "finding", "why_it_matters", "action_implication"]
    missing = require_fields(payload, required)
    errors = [f"missing:{m}" for m in missing]
    for key in required:
        if key in payload and not str(payload[key]).strip():
            errors.append(f"empty:{key}")
    return (len(errors) == 0, errors)


def validate_manifest_payload(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    required = ["run_id", "profile", "created_at", "artifacts"]
    missing = require_fields(payload, required)
    errors = [f"missing:{m}" for m in missing]
    if "artifacts" in payload and not isinstance(payload["artifacts"], list):
        errors.append("invalid:artifacts_not_list")
    if "artifacts" in payload and isinstance(payload["artifacts"], list):
        for idx, artifact in enumerate(payload["artifacts"]):
            if not isinstance(artifact, dict):
                errors.append(f"invalid:artifact_{idx}_not_object")
                continue
            artifact_missing = require_fields(
                artifact, ["artifact_id", "stage_id", "artifact_type", "path", "format"]
            )
            errors.extend([f"missing:artifact_{idx}:{field}" for field in artifact_missing])
            if artifact_missing:
                continue
            artifact_type = str(artifact["artifact_type"])
            artifact_format = str(artifact["format"])
            allowed_formats = ARTIFACT_FORMAT_RULES.get(artifact_type)
            if allowed_formats is None:
                errors.append(f"invalid:artifact_{idx}:artifact_type:{artifact_type}")
                continue
            if artifact_format not in allowed_formats:
                errors.append(
                    f"invalid:artifact_{idx}:format_for_type:{artifact_type}:{artifact_format}"
                )
    return (len(errors) == 0, errors)
