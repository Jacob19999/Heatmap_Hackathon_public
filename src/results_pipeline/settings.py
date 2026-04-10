from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

OFFICIAL_MVP_STAGES = ["00", "01", "02", "03", "04", "05", "08", "09"]
OFFICIAL_FULL_STAGES = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"]
VALID_STAGE_IDS = set(OFFICIAL_FULL_STAGES)


class ConfigError(ValueError):
    """Raised when pipeline configuration is invalid."""


@dataclass(frozen=True)
class RuntimeConfig:
    raw: dict[str, Any]
    source_paths: list[Path]

    @property
    def profile(self) -> str:
        return str(self.raw.get("profile", "mvp"))

    @property
    def stages(self) -> list[str]:
        stages = self.raw.get("stages")
        if isinstance(stages, list):
            return [str(s) for s in stages]
        return []

    @property
    def scenario(self) -> str:
        return str(self.raw.get("scenario", "ground_only"))


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise ConfigError(
            "PyYAML is required to parse config files. Install with `pip install pyyaml`."
        ) from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config must parse to a mapping: {path}")
    return data


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def load_runtime_config(
    profile_path: Path,
    scenario_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> RuntimeConfig:
    """
    Merge config with precedence:
    default < profile < scenario < CLI overrides
    """
    profile_path = profile_path.resolve()
    repo_root = profile_path.parent.parent if profile_path.name != "default.yaml" else profile_path.parent.parent
    default_path = repo_root / "configs" / "default.yaml"
    merged = _read_yaml(default_path) if default_path.exists() else {}
    merged = _deep_merge(merged, _read_yaml(profile_path))
    source_paths = [p for p in [default_path if default_path.exists() else None, profile_path] if p is not None]

    if scenario_path is not None:
        scenario_path = scenario_path.resolve()
        merged = _deep_merge(merged, _read_yaml(scenario_path))
        source_paths.append(scenario_path)

    if cli_overrides:
        merged = _deep_merge(merged, cli_overrides)

    validate_runtime_config(merged)
    return RuntimeConfig(raw=merged, source_paths=source_paths)


def validate_runtime_config(raw: dict[str, Any]) -> None:
    profile = str(raw.get("profile", ""))
    if profile and profile not in {"mvp", "full", "stage"}:
        raise ConfigError(f"Unsupported profile '{profile}'.")

    scenario = str(raw.get("scenario", "ground_only"))
    if scenario not in {"ground_only", "ground_plus_air"}:
        raise ConfigError(f"Unsupported scenario '{scenario}'.")

    stages = raw.get("stages", [])
    if stages and not isinstance(stages, list):
        raise ConfigError("Config field 'stages' must be a list.")
    if isinstance(stages, list):
        stage_ids = [str(stage) for stage in stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ConfigError("Config field 'stages' contains duplicate stage IDs.")
        invalid_stage_ids = [stage for stage in stage_ids if stage not in VALID_STAGE_IDS]
        if invalid_stage_ids:
            raise ConfigError(f"Unsupported stage IDs in config: {invalid_stage_ids}")
        if profile == "mvp" and stage_ids and stage_ids != OFFICIAL_MVP_STAGES:
            raise ConfigError(
                f"MVP profile must use the official stage list: {OFFICIAL_MVP_STAGES}"
            )
        if profile == "full" and stage_ids and stage_ids != OFFICIAL_FULL_STAGES:
            raise ConfigError(
                f"Full profile must use the official stage list: {OFFICIAL_FULL_STAGES}"
            )

    air_assumptions = raw.get("air_assumptions", {})
    if air_assumptions is None:
        air_assumptions = {}
    if not isinstance(air_assumptions, dict):
        raise ConfigError("Config field 'air_assumptions' must be a mapping when provided.")

    if scenario == "ground_plus_air":
        required_air_keys = ["air_cap_minutes", "air_speed_factor"]
        missing_air_keys = [key for key in required_air_keys if key not in air_assumptions]
        if missing_air_keys:
            raise ConfigError(
                "ground_plus_air scenario requires air_assumptions keys: "
                + ", ".join(missing_air_keys)
            )
        if float(air_assumptions["air_cap_minutes"]) <= 0:
            raise ConfigError("air_assumptions.air_cap_minutes must be positive.")
        if float(air_assumptions["air_speed_factor"]) <= 0:
            raise ConfigError("air_assumptions.air_speed_factor must be positive.")
    elif air_assumptions.get("enabled"):
        raise ConfigError("air_assumptions.enabled can only be true for ground_plus_air.")
