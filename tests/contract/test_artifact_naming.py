from __future__ import annotations

import pytest

from src.results_pipeline.utils.validation import ArtifactValidationError, validate_artifact_name


def test_validate_artifact_name_accepts_stage_centric_pattern() -> None:
    validate_artifact_name("03_metrics_access_burden_by_ruca_ground_only.parquet")
    validate_artifact_name("07_figures_air_sensitivity_delta_ground_plus_air.png")


@pytest.mark.parametrize(
    "name",
    [
        "metrics_access_burden_ground_only.parquet",
        "3_metrics_access_burden_ground_only.parquet",
        "03-metrics-access-burden.parquet",
        "03_metrics_access_burden.parquet",
    ],
)
def test_validate_artifact_name_rejects_invalid_pattern(name: str) -> None:
    with pytest.raises(ArtifactValidationError):
        validate_artifact_name(name)
