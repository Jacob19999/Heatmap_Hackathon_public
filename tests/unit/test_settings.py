from __future__ import annotations

from pathlib import Path

from src.results_pipeline.settings import RuntimeConfig, _deep_merge, validate_runtime_config


def test_deep_merge_overrides_nested_values() -> None:
    base = {"a": 1, "nested": {"x": 1, "y": 2}}
    overlay = {"nested": {"y": 99}, "b": 2}
    merged = _deep_merge(base, overlay)
    assert merged["a"] == 1
    assert merged["b"] == 2
    assert merged["nested"]["x"] == 1
    assert merged["nested"]["y"] == 99


def test_validate_runtime_config_accepts_known_values() -> None:
    validate_runtime_config(
        {
            "profile": "mvp",
            "scenario": "ground_only",
            "stages": ["00", "01", "02", "03", "04", "05", "08", "09"],
        }
    )


def test_runtime_config_properties() -> None:
    cfg = RuntimeConfig(raw={"profile": "full", "scenario": "ground_plus_air", "stages": ["00"]}, source_paths=[Path("x")])
    assert cfg.profile == "full"
    assert cfg.scenario == "ground_plus_air"
    assert cfg.stages == ["00"]
