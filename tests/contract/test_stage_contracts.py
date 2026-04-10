from __future__ import annotations

from src.results_pipeline.registry import create_default_registry


def test_default_registry_stage_contract_completeness() -> None:
    registry = create_default_registry()
    required = ["stage_id", "name", "question", "description"]
    for stage in registry.stages.values():
        as_dict = {
            "stage_id": stage.stage_id,
            "name": stage.name,
            "question": stage.question,
            "description": stage.description,
        }
        for field in required:
            assert as_dict[field], f"{stage.stage_id} missing {field}"
