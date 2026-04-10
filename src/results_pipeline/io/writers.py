from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..contracts.artifacts import ArtifactManifest, FindingRecord
from ..contracts.schemas import validate_finding_payload, validate_manifest_payload


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    _ensure_parent(path)
    df.to_csv(path, index=False)
    return path


def write_parquet(df: pd.DataFrame, path: Path) -> Path:
    _ensure_parent(path)
    df.to_parquet(path, index=False)
    return path


def write_manifest(manifest: ArtifactManifest, path: Path) -> Path:
    payload = manifest.to_dict()
    ok, errors = validate_manifest_payload(payload)
    if not ok:
        raise ValueError(f"Invalid manifest payload: {errors}")
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_finding(record: FindingRecord, path: Path) -> Path:
    payload = record.to_dict()
    ok, errors = validate_finding_payload(payload)
    if not ok:
        raise ValueError(f"Invalid finding payload: {errors}")
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
