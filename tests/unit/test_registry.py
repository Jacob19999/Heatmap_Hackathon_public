from __future__ import annotations

from src.results_pipeline.registry import create_default_registry


def test_registry_contains_required_stages() -> None:
    registry = create_default_registry()
    for stage_id in ["00", "01", "02", "03", "04", "05", "08", "09"]:
        assert stage_id in registry.stages


def test_registry_get_returns_metadata() -> None:
    registry = create_default_registry()
    stage = registry.get("03")
    assert stage.stage_id == "03"
    assert stage.question
    assert stage.description
