from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class ValidationError(RuntimeError):
    pass


class ArtifactValidationError(ValidationError):
    pass


class SchemaValidationError(ValidationError):
    pass


def require_paths_exist(paths: list[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise ValidationError(f"Missing required path(s): {missing}")


def require_columns(columns: list[str], required: list[str]) -> None:
    missing = [c for c in required if c not in columns]
    if missing:
        raise ValidationError(f"Missing required column(s): {missing}")


def validate_schema_shape(payload: dict[str, Any], required_fields: list[str], name: str) -> None:
    missing = [k for k in required_fields if k not in payload]
    if missing:
        raise SchemaValidationError(f"{name} missing required field(s): {missing}")


def require_artifacts_present(paths: list[Path], context: str = "") -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        suffix = f" ({context})" if context else ""
        raise ArtifactValidationError(f"Missing artifact(s){suffix}: {missing}")


def validate_artifact_name(name: str) -> None:
    # Stage-centric convention: "<stage_id>_<group>_<name>_<scenario>.<ext>"
    pattern = r"^(0[0-9]|10)_[a-z0-9]+_[a-z0-9_]+_(ground_only|ground_plus_air)\.[a-z0-9]+$"
    if not re.match(pattern, name):
        raise ArtifactValidationError(f"Invalid artifact naming convention: {name}")
