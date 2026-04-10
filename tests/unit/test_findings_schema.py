from __future__ import annotations

from src.results_pipeline.contracts.schemas import validate_finding_payload


def test_validate_finding_payload_success() -> None:
    ok, errors = validate_finding_payload(
        {
            "stage_id": "03",
            "question": "How unequal is ground access burden across RUCA classes?",
            "finding": "Rural counties show higher travel burden.",
            "why_it_matters": "National averages hide long-tail inequity.",
            "action_implication": "Prioritize transfer-aware routing in high-burden rural regions.",
        }
    )
    assert ok is True
    assert errors == []


def test_validate_finding_payload_missing_fields() -> None:
    ok, errors = validate_finding_payload({"stage_id": "03"})
    assert ok is False
    assert any(err.startswith("missing:") for err in errors)
