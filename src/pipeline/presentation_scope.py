from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from . import config


@dataclass(frozen=True)
class DatasetProfile:
    """Presentation/data scope description for precomputed outputs."""

    profile_id: str
    display_name: str
    scope_level: str  # "state", "region", or "national"

    origin_state_fips: tuple[str, ...]
    destination_state_filter: tuple[str, ...]

    matrix_raw_path: str
    matrix_filled_path: str
    output_prefix: str

    default_scenario: str  # e.g. "ground_only"
    enabled_scenarios: tuple[str, ...]

    default_map_center: tuple[float, float]
    default_map_zoom: float

    notes: str = ""


def _tuple(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(items)


MN_HIGH_DETAIL_PROFILE = DatasetProfile(
    profile_id="mn_high_detail",
    display_name="Minnesota High Detail",
    scope_level="state",
    origin_state_fips=("27",),
    destination_state_filter=("MN", "ND", "SD", "IA", "WI"),
    matrix_raw_path=str(
        (config.TABLES_DIR / "valhalla_mn_hospitals_timedist.parquet").resolve()
    ),
    matrix_filled_path=str(
        (
            config.TABLES_DIR
            / "valhalla_mn_hospitals_timedist_filled.parquet"
        ).resolve()
    ),
    output_prefix="mn_high_detail",
    default_scenario="ground_only",
    enabled_scenarios=("ground_only", "ground_plus_air"),
    default_map_center=(46.0, -94.0),  # Rough center of Minnesota
    default_map_zoom=6.0,
    notes=(
        "Minnesota-only tract-detail presentation scope. Uses national "
        "ingestion/routing but exports MN-focused outputs with regional cross-border "
        "destinations preserved for border tracts."
    ),
)

USA_LOW_DETAIL_COUNTY_PROFILE = DatasetProfile(
    profile_id="usa_low_detail_county",
    display_name="USA Low Detail (County)",
    scope_level="national",
    origin_state_fips=(),  # all states implicitly included
    destination_state_filter=(),
    matrix_raw_path=str(
        (config.TABLES_DIR / "usa_low_detail_county_county_travel_time_matrix.parquet").resolve()
    ),
    matrix_filled_path=str(
        (config.TABLES_DIR / "usa_low_detail_county_county_travel_time_matrix.parquet").resolve()
    ),
    output_prefix="usa_low_detail_county",
    default_scenario="ground_only",
    enabled_scenarios=("ground_only", "ground_plus_air"),
    default_map_center=(39.5, -98.35),  # Rough center of contiguous US
    default_map_zoom=4.0,
    notes=(
        "National county-level low-detail presentation scope. Uses national "
        "BEI and access outputs aggregated to counties for fast national views."
    ),
)

_PROFILES: dict[str, DatasetProfile] = {
    MN_HIGH_DETAIL_PROFILE.profile_id: MN_HIGH_DETAIL_PROFILE,
    USA_LOW_DETAIL_COUNTY_PROFILE.profile_id: USA_LOW_DETAIL_COUNTY_PROFILE,
    # Backwards compatible alias for earlier MN MVP usage
    "mn_mvp": MN_HIGH_DETAIL_PROFILE,
}


def get_profile(profile_id: str | None = None) -> DatasetProfile:
    """Return the configured dataset profile (mn_high_detail by default)."""
    key = profile_id or config.DEFAULT_PROFILE_ID
    try:
        return _PROFILES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown dataset profile: {key}") from exc


def list_profiles() -> list[DatasetProfile]:
    """Return all known dataset profiles."""
    return list(_PROFILES.values())

