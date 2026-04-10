from __future__ import annotations

from pathlib import Path

import pytest

from src.results_pipeline.settings import ConfigError, load_runtime_config, validate_runtime_config


def test_load_runtime_config_merges_default_profile_and_scenario(tmp_path: Path) -> None:
    configs = tmp_path / "configs"
    scenarios = configs / "scenarios"
    scenarios.mkdir(parents=True, exist_ok=True)

    (configs / "default.yaml").write_text(
        "\n".join(
            [
                "profile: mvp",
                "scenario: ground_only",
                "data:",
                "  cache_dir: data/cache",
                "routing:",
                "  transfer_penalty_minutes: 45",
            ]
        ),
        encoding="utf-8",
    )
    (configs / "mvp.yaml").write_text(
        "\n".join(
            [
                "profile: mvp",
                "stages:",
                '  - "00"',
                '  - "01"',
                '  - "02"',
                '  - "03"',
                '  - "04"',
                '  - "05"',
                '  - "08"',
                '  - "09"',
            ]
        ),
        encoding="utf-8",
    )
    (scenarios / "ground_plus_air.yaml").write_text(
        "\n".join(
            [
                "scenario: ground_plus_air",
                "air_assumptions:",
                "  enabled: true",
                "  air_cap_minutes: 60",
                "  air_speed_factor: 0.4",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_runtime_config(configs / "mvp.yaml", scenario_path=scenarios / "ground_plus_air.yaml")

    assert cfg.profile == "mvp"
    assert cfg.scenario == "ground_plus_air"
    assert cfg.stages == ["00", "01", "02", "03", "04", "05", "08", "09"]
    assert cfg.raw["routing"]["transfer_penalty_minutes"] == 45
    assert cfg.raw["air_assumptions"]["enabled"] is True
    assert len(cfg.source_paths) == 3


def test_validate_runtime_config_rejects_non_official_mvp_stage_list() -> None:
    with pytest.raises(ConfigError):
        validate_runtime_config(
            {
                "profile": "mvp",
                "scenario": "ground_only",
                "stages": ["00", "01", "02"],
            }
        )


def test_validate_runtime_config_requires_air_assumptions_for_ground_plus_air() -> None:
    with pytest.raises(ConfigError):
        validate_runtime_config(
            {
                "profile": "full",
                "scenario": "ground_plus_air",
                "stages": ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"],
            }
        )


def test_validate_runtime_config_rejects_air_enabled_for_ground_only() -> None:
    with pytest.raises(ConfigError):
        validate_runtime_config(
            {
                "profile": "mvp",
                "scenario": "ground_only",
                "stages": ["00", "01", "02", "03", "04", "05", "08", "09"],
                "air_assumptions": {"enabled": True, "air_cap_minutes": 60, "air_speed_factor": 0.4},
            }
        )
