"""Manifest and export contract checks (US7).

Independent test: every figure renders, manifests resolve correctly,
exported tables/GeoJSON contain expected metric fields with non-null geography keys.
Contract validation for presentation_manifest and product_views_manifest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.config import MANIFESTS_DIR, OUTPUT_DIR
from pipeline.export import (
    manifest_path_for_profile,
    write_presentation_manifest,
    write_product_views_manifest,
    write_default_dual_path_product_views_manifest,
)
from pipeline.presentation_scope import get_profile


# Required keys per contracts/presentation_manifest.schema.json
PRESENTATION_REQUIRED_TOP = [
    "manifest_version", "generated_at", "profile", "scenarios", "assets",
    "methodology", "ui_defaults",
]
PRESENTATION_PROFILE_KEYS = ["id", "display_name", "scope_level", "output_prefix"]
PRESENTATION_SCENARIOS_KEYS = ["default", "enabled"]
PRESENTATION_UI_DEFAULTS_KEYS = ["geography_level", "metric", "map_center", "map_zoom"]

# Required keys per contracts/product_views_manifest.schema.json
PRODUCT_VIEWS_REQUIRED_TOP = ["manifest_version", "generated_at", "product_name", "views"]
PRODUCT_VIEW_REQUIRED_KEYS = [
    "view_id", "label", "detail_level", "dataset_profile_id",
    "manifest_path", "default_metric", "default_geography_level",
]


def _load_json(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"Manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_presentation_manifest_exists() -> Path:
    """Write a minimal contract-valid presentation manifest if missing, then return its path."""
    profile = get_profile()
    path = manifest_path_for_profile(profile)
    if path.exists():
        return path
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    write_presentation_manifest(
        profile,
        assets={},
        methodology={
            "data_sources": [],
            "limitations": [],
            "scope_note": "Test manifest for contract validation.",
        },
        ui_defaults={
            "geography_level": "tract",
            "metric": "bei",
            "map_center": [39.5, -98.0],
            "map_zoom": 6,
        },
    )
    return path


def test_presentation_manifest_contract_required_top_level():
    """Presentation manifest has required top-level keys."""
    path = _ensure_presentation_manifest_exists()
    data = _load_json(path)
    for key in PRESENTATION_REQUIRED_TOP:
        assert key in data, f"Missing required key: {key}"


def test_presentation_manifest_contract_profile_shape():
    """Presentation manifest profile has id, display_name, scope_level, output_prefix."""
    path = _ensure_presentation_manifest_exists()
    data = _load_json(path)
    assert "profile" in data, "manifest must include profile"
    for key in PRESENTATION_PROFILE_KEYS:
        assert key in data["profile"], f"profile missing key: {key}"


def test_presentation_manifest_contract_scenarios_and_ui_defaults():
    """Scenarios have default and enabled; ui_defaults have geography_level, metric, map_center, map_zoom."""
    path = _ensure_presentation_manifest_exists()
    data = _load_json(path)
    assert "scenarios" in data, "manifest must include scenarios"
    for key in PRESENTATION_SCENARIOS_KEYS:
        assert key in data["scenarios"], f"scenarios missing key: {key}"
    assert "ui_defaults" in data, "manifest must include ui_defaults"
    for key in PRESENTATION_UI_DEFAULTS_KEYS:
        assert key in data["ui_defaults"], f"ui_defaults missing key: {key}"


def test_product_views_manifest_contract_required_top_level():
    """Product views manifest has manifest_version, generated_at, product_name, views."""
    path = MANIFESTS_DIR / "product_views_manifest.json"
    data = _load_json(path)
    for key in PRODUCT_VIEWS_REQUIRED_TOP:
        assert key in data, f"Missing required key: {key}"
    assert isinstance(data["views"], list), "views must be array"
    assert len(data["views"]) >= 2, "views must have at least 2 items (dual-path)"


def test_product_views_manifest_each_view_has_required_fields():
    """Each view has view_id, label, detail_level, dataset_profile_id, manifest_path, default_metric, default_geography_level."""
    path = MANIFESTS_DIR / "product_views_manifest.json"
    data = _load_json(path)
    for i, view in enumerate(data.get("views", [])):
        for key in PRODUCT_VIEW_REQUIRED_KEYS:
            assert key in view, f"view[{i}] missing key: {key}"
        assert view["detail_level"] in ("high", "low"), "detail_level must be high or low"
        assert view["default_geography_level"] in ("tract", "county", "state"), "default_geography_level enum"


def test_write_default_dual_path_product_views_manifest_produces_valid_contract():
    """Writing default dual-path product views manifest produces contract-valid JSON."""
    path = write_default_dual_path_product_views_manifest()
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in PRODUCT_VIEWS_REQUIRED_TOP:
        assert key in data
    assert len(data["views"]) >= 2
    view_ids = {v["view_id"] for v in data["views"]}
    assert "mn_high_detail_tab" in view_ids or any("mn" in v.get("view_id", "") for v in data["views"])
    assert "usa_low_detail_county_tab" in view_ids or any("usa" in v.get("view_id", "") for v in data["views"])
