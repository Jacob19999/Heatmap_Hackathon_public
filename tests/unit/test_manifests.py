from __future__ import annotations

import json

from src.results_pipeline.contracts.artifacts import ArtifactManifest, ArtifactRecord


def test_manifest_to_dict_contains_expected_fields() -> None:
    manifest = ArtifactManifest(
        run_id="run123",
        profile="mvp",
        artifacts=[
            ArtifactRecord(
                artifact_id="a1",
                stage_id="03",
                artifact_type="dataset",
                path="outputs/metrics/03_metrics_access_burden_ground_only.parquet",
                format="parquet",
            )
        ],
    )
    payload = manifest.to_dict()
    assert payload["run_id"] == "run123"
    assert payload["profile"] == "mvp"
    assert isinstance(payload["artifacts"], list)
    assert payload["artifacts"][0]["stage_id"] == "03"


def test_manifest_payload_is_json_serializable() -> None:
    manifest = ArtifactManifest(run_id="run456", profile="full")
    serialized = json.dumps(manifest.to_dict())
    assert "run456" in serialized
