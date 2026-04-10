# Data Model: BEI Analytics Pipeline

**Feature**: 001-phase1-bei-analytics
**Date**: 2026-03-14

This document defines all data entities, their fields, relationships, and lifecycle in the Phase 1 pipeline.

---

## Entity Relationship Overview

```text
NIRD Facilities ──────┐
                      ├──► Analytic Table (tract-level) ──► BEI Records
ACS Population ───────┤         │                              │
TIGER/Line Geometry ──┤         │                              ├──► Aggregated (county/state)
RUCA Codes ───────────┘         │                              ├──► Hotspot Clusters
                                ▼                              └──► Precomputed Payloads
                      Travel-Time Matrix
                                │
FAA Heliports ─────────────────►│ (air scenario)
```

---

## 1. Facility

A hospital record from NIRD, geocoded and classified.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `facility_id` | string | NIRD `AHA_ID` | Unique facility identifier |
| `hospital_name` | string | NIRD | Facility name |
| `state` | string | NIRD | State abbreviation |
| `county` | string | NIRD | County name |
| `zip_code` | string | NIRD | 5-digit ZIP |
| `address` | string | NIRD | Street address |
| `latitude` | float | Geocoded | WGS84 latitude |
| `longitude` | float | Geocoded | WGS84 longitude |
| `tract_geoid` | string | Spatial join | 11-digit census tract FIPS |
| `is_burn_center` | bool | Derived | True if `BURN_ADULT=1` OR `BURN_PEDS=1` |
| `is_definitive` | bool | Derived | Alias for `is_burn_center` (set D) |
| `is_stabilization` | bool | Derived | True if trauma-capable and not definitive (set S) |
| `burn_adult` | bool | NIRD | Adult burn capability |
| `burn_peds` | bool | NIRD | Pediatric burn capability |
| `aba_verified` | bool | NIRD | ABA verification status |
| `bc_state_designated` | bool | NIRD | State burn-center designation |
| `trauma_adult` | bool | NIRD | Any adult trauma capability |
| `trauma_peds` | bool | NIRD | Any pediatric trauma capability |
| `adult_trauma_l1` | bool | NIRD | Adult Level I trauma |
| `adult_trauma_l2` | bool | NIRD | Adult Level II trauma |
| `peds_trauma_l1` | bool | NIRD | Pediatric Level I trauma |
| `peds_trauma_l2` | bool | NIRD | Pediatric Level II trauma |
| `total_beds` | int | NIRD | Total staffed beds |
| `burn_beds` | int | NIRD | Burn-dedicated beds |
| `supply_weight` | float | Derived | q_j^(S) — capability weight for S component |
| `peds_weight` | float | Derived | q_j^(P) — capability weight for P component |
| `geocode_method` | string | Derived | How coordinates were obtained (address/zip_centroid/manual) |

**Validation rules**:
- `facility_id` must be unique and non-null
- `latitude` in [-90, 90], `longitude` in [-180, -60] (continental US + AK/HI)
- `burn_beds` ≥ 0; null treated as 0 for non-burn facilities
- Exactly one of: is_definitive, is_stabilization, or neither (mutually exclusive classification)

---

## 2. Census Tract

The geographic unit of analysis, enriched with population and rurality.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `tract_geoid` | string | TIGER/Line `GEOID` | 11-digit FIPS (state+county+tract) |
| `state_fips` | string | Derived | 2-digit state FIPS |
| `county_fips` | string | Derived | 5-digit county FIPS (state+county) |
| `centroid_lat` | float | TIGER/Line `INTPTLAT` | Internal point latitude |
| `centroid_lon` | float | TIGER/Line `INTPTLON` | Internal point longitude |
| `land_area_sqm` | float | TIGER/Line `ALAND` | Land area in square meters |
| `total_pop` | int | ACS `B01003` | Total population |
| `child_pop` | int | ACS `B09001` | Population under 18 |
| `ruca_code` | float | RUCA | Primary RUCA code (1–10) |
| `is_rural` | bool | Derived | True if `ruca_code` ≥ 4 |
| `geometry` | Polygon | TIGER/Line | Tract boundary geometry |

**Optional fields** (secondary overlays):
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `svi_overall` | float | CDC SVI | Overall social vulnerability percentile |
| `svi_theme1` | float | CDC SVI | Socioeconomic status theme |
| `svi_theme2` | float | CDC SVI | Household characteristics theme |
| `svi_theme3` | float | CDC SVI | Racial/ethnic minority status theme |
| `svi_theme4` | float | CDC SVI | Housing type / transportation theme |

**Validation rules**:
- `tract_geoid` must be exactly 11 characters and unique
- `total_pop` ≥ 0; tracts with `total_pop` = 0 are excluded from BEI computation
- `child_pop` ≤ `total_pop`
- `ruca_code` in [1.0, 10.0]

---

## 3. Travel-Time Matrix

Origin-destination travel times by mode and scenario.

| Field | Type | Description |
|-------|------|-------------|
| `origin_id` | string | Tract GEOID (centroid) or facility_id |
| `destination_id` | string | Facility ID |
| `mode` | enum | `road` or `air` |
| `scenario` | enum | `ground_only` or `ground_plus_air` |
| `travel_time_min` | float | Total travel time in minutes; +∞ if infeasible |
| `distance_km` | float | Route distance in km (road mode only) |
| `is_feasible` | bool | Whether this mode is allowed under the scenario |

**Sub-fields for air mode** (when `mode=air`):
| Field | Type | Description |
|-------|------|-------------|
| `dispatch_min` | float | Dispatch delay (scenario constant) |
| `ground_to_launch_min` | float | Drive time to nearest airport/heliport |
| `flight_min` | float | Air flight time (distance / cruise speed) |
| `landing_to_facility_min` | float | Drive time from landing point to destination |
| `handoff_min` | float | Post-landing handoff time (scenario constant) |
| `launch_airport_id` | string | FAA LocationID of departure heliport/airport |
| `landing_airport_id` | string | FAA LocationID of arrival heliport/airport |

**Validation rules**:
- `travel_time_min` > 0 for feasible pairs; `+inf` for infeasible
- Air mode `is_feasible` = False under `ground_only` scenario
- `ground_to_launch_min` ≤ configurable threshold (default 30 min) for air feasibility

---

## 4. BEI Record

Tract-level computed metrics for a given transport scenario.

| Field | Type | Description |
|-------|------|-------------|
| `tract_geoid` | string | 11-digit FIPS |
| `scenario` | enum | `ground_only` or `ground_plus_air` |
| `s_raw` | float | Raw specialized supply accessibility A_i^(S) |
| `s_score` | float | Normalized S component [0, 1] |
| `t_dir` | float | Direct access time to nearest definitive center (min) |
| `t_trans` | float | Transfer-aware access time (min) |
| `t_sys` | float | System time = min(t_dir, t_trans) (min) |
| `t_stab` | float | Time to nearest stabilization hospital (min) |
| `t_delta` | float | Tier penalty Δ = max(0, t_stab − 30) |
| `t_score` | float | Normalized T component [0, 1] |
| `p_raw` | float | Raw pediatric accessibility A_i^(P) |
| `p_score` | float | Normalized P component [0, 1] |
| `c_raw` | float | Raw structural bed accessibility A_i^(C) |
| `c_score` | float | Normalized C component [0, 1] |
| `bei` | float | Composite BEI [0, 100] |
| `bei_percentile` | float | National percentile rank [0, 100] |
| `nearest_burn_time` | float | Companion: time to nearest definitive burn center (min) |
| `centers_per_100k` | float | Companion: weighted burn centers per 100k pop |
| `beds_per_100k` | float | Companion: accessible burn beds per 100k pop |
| `peds_access` | float | Companion: pediatric accessibility score |
| `access_pathway` | enum | `direct` or `transfer` — which pathway determines t_sys |

**Validation rules**:
- All `*_score` fields in [0, 1]
- `bei` in [0, 100]
- `t_sys` ≤ `t_dir` (by construction)
- `bei` = 100 × (0.25 × s_score + 0.30 × t_score + 0.20 × p_score + 0.25 × c_score) within floating-point tolerance

---

## 5. Aggregated Record

Population-weighted rollup at county or state level.

| Field | Type | Description |
|-------|------|-------------|
| `geo_id` | string | 5-digit county FIPS or 2-digit state FIPS |
| `geo_level` | enum | `county` or `state` |
| `geo_name` | string | County or state name |
| `scenario` | enum | Transport scenario |
| `total_pop` | int | Aggregated population |
| `child_pop` | int | Aggregated child population |
| `tract_count` | int | Number of tracts in this geography |
| `rural_tract_pct` | float | Percentage of tracts classified as rural |
| `bei_mean` | float | Population-weighted mean BEI |
| `bei_median` | float | Median tract BEI |
| `bei_p25` | float | 25th percentile tract BEI |
| `bei_p75` | float | 75th percentile tract BEI |
| `s_mean` | float | Pop-weighted mean S |
| `t_mean` | float | Pop-weighted mean T |
| `p_mean` | float | Pop-weighted mean P |
| `c_mean` | float | Pop-weighted mean C |
| `nearest_burn_time_median` | float | Median nearest burn time |
| `centers_per_100k` | float | Burn centers per 100k population |
| `beds_per_100k` | float | Burn beds per 100k population |
| `burn_center_count` | int | Number of burn centers in geography |
| `burn_bed_total` | int | Total burn beds in geography |

---

## 6. Hotspot Cluster

Result of spatial hotspot detection and clustering.

| Field | Type | Description |
|-------|------|-------------|
| `tract_geoid` | string | 11-digit FIPS |
| `gi_star_z` | float | Getis-Ord Gi* z-score |
| `gi_star_p` | float | Gi* p-value |
| `gi_star_class` | enum | `hot` (sig high), `cold` (sig low), `ns` (not significant) |
| `moran_local_i` | float | Local Moran's I statistic |
| `moran_p` | float | Local Moran's I p-value |
| `moran_class` | enum | `HH`, `LL`, `HL`, `LH`, `ns` |
| `cluster_id` | int | K-means or HDBSCAN cluster label |
| `archetype_label` | string | Human-readable archetype name |
| `archetype_dominant_component` | string | Which BEI component drives this archetype (S/T/P/C) |
| `priority_score` | float | BEI × (1 + λ·NeedOverlay) |
| `need_overlay` | float | α·Norm(Pop) + (1−α)·Norm(ChildPop) |
| `stability_pct` | float | % of sensitivity scenarios where tract remains a hotspot |
| `stability_class` | enum | `persistent` (≥80%), `conditional` (50–79%), `unstable` (<50%) |

---

## 7. Scenario Delta

Comparison between transport scenarios.

| Field | Type | Description |
|-------|------|-------------|
| `tract_geoid` | string | 11-digit FIPS |
| `bei_ground` | float | BEI under ground-only scenario |
| `bei_air` | float | BEI under ground-plus-air scenario |
| `bei_delta` | float | `bei_ground` − `bei_air` (positive = air improves equity) |
| `t_sys_ground` | float | System time under ground-only (min) |
| `t_sys_air` | float | System time under ground-plus-air (min) |
| `t_delta` | float | Time improvement from air scenario (min) |
| `air_feasible` | bool | Whether this tract has plausible air access |
| `air_materially_helps` | bool | `bei_delta` > configurable threshold (e.g., 2 points) |

---

## 8. FAA Heliport/Airport

Launch and landing infrastructure for air scenario.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `location_id` | string | FAA | Unique airport/heliport ID |
| `facility_type` | enum | FAA | `HELIPORT`, `AIRPORT`, `SEAPLANE BASE`, etc. |
| `latitude` | float | FAA `ARPLatitude` | WGS84 latitude |
| `longitude` | float | FAA `ARPLongitude` | WGS84 longitude |
| `status` | string | FAA `StatusCode` | Operational status (O = operational) |
| `state` | string | FAA | State |
| `city` | string | FAA | City |

**Filter**: Only include records where `status = 'O'` (operational) and `facility_type` in (`HELIPORT`, `AIRPORT`).

---

## 9. Precomputed Payload

Final export artifacts for Phase 2 consumption.

| Artifact | Format | Contents |
|----------|--------|----------|
| `tract_ground_v1.parquet` | Parquet | All BEI Record fields for ground-only scenario |
| `tract_air_v1.parquet` | Parquet | All BEI Record fields for ground-plus-air scenario |
| `tract_delta_v1.parquet` | Parquet | All Scenario Delta fields |
| `county_ground_v1.parquet` | Parquet | County-level Aggregated Records |
| `state_ground_v1.parquet` | Parquet | State-level Aggregated Records |
| `hotspot_v1.parquet` | Parquet | All Hotspot Cluster fields |
| `facilities_v1.parquet` | Parquet | All Facility fields with weights |
| `tract_bei_ground.geojson` | GeoJSON | Tract geometry + BEI + components (ground) |
| `tract_bei_air.geojson` | GeoJSON | Tract geometry + BEI + components (air) |
| `tract_delta.geojson` | GeoJSON | Tract geometry + scenario delta fields |
| `tract_hotspot.geojson` | GeoJSON | Tract geometry + hotspot/archetype fields |
| `facilities.geojson` | GeoJSON | Facility points + designation + weights |
| `county_bei_ground.geojson` | GeoJSON | County geometry + aggregated BEI |

**Version convention**: `_v1` increments when schema changes. Filenames include scenario for clarity.

**Scope convention**: Assets should also include a dataset-profile prefix when the build is not national, for example `mn_mvp_tract_ground_v1.parquet` or `mn_mvp_tract_bei_ground.geojson`.

---

## 10. Dataset Profile

Declarative configuration describing the active presentation/data scope.

| Field | Type | Description |
|-------|------|-------------|
| `profile_id` | string | Stable identifier such as `mn_mvp` or `national_full` |
| `display_name` | string | Human-readable label shown to analysts and frontend users |
| `scope_level` | enum | `state`, `region`, or `national` |
| `origin_state_fips` | array[string] | State FIPS codes included as tract origins |
| `destination_state_filter` | array[string] | State abbreviations or FIPS codes allowed for destination facilities |
| `matrix_raw_path` | string | Primary raw matrix path for this scope |
| `matrix_filled_path` | string | Preferred post-processed matrix path for this scope |
| `output_prefix` | string | Prefix applied to exported payload names |
| `default_scenario` | enum | Default scenario for this profile |
| `enabled_scenarios` | array[enum] | Published scenarios available to the frontend |
| `default_map_center` | array[float] | `[lat, lon]` center for the frontend map |
| `default_map_zoom` | float | Initial map zoom for the active scope |
| `notes` | string | Analyst-facing notes or caveats about the scope |

**Validation rules**:
- `profile_id` must be unique and filesystem-safe
- `origin_state_fips` must be non-empty for `state` and `region` scopes
- `output_prefix` must match `profile_id` unless a documented exception exists
- `default_scenario` must appear in `enabled_scenarios`

**Published profiles for the current product design**:
- `mn_high_detail`: Minnesota tract-level detail for the high-detail tab
- `usa_low_detail_county`: USA county-level detail for the low-detail tab

---

## 11. Presentation Manifest

Frontend-facing index of all payloads generated for a dataset profile.

| Field | Type | Description |
|-------|------|-------------|
| `manifest_version` | string | Contract version, e.g. `1.0.0` |
| `generated_at` | datetime string | UTC generation timestamp |
| `profile_id` | string | Active Dataset Profile identifier |
| `display_name` | string | Human-readable name for the scope |
| `scope_level` | enum | `state`, `region`, or `national` |
| `geography_summary` | object | Counts and labels for included tracts/counties/states |
| `default_scenario` | enum | Scenario selected on initial load |
| `enabled_scenarios` | array[enum] | Published scenarios for this build |
| `assets` | object | Named table and GeoJSON payloads for the frontend |
| `facility_assets` | object | Optional point-layer payloads such as facilities or heliports |
| `methodology` | object | Data source names, vintage, limitations, and scope notes |
| `ui_defaults` | object | Suggested metric, geography level, map center, zoom, and narrative order |

**Validation rules**:
- Every asset path must be relative to the exported output root or an absolute file URI agreed by the frontend
- `profile_id` must correspond to a defined Dataset Profile
- `enabled_scenarios` must match the scenarios actually exported in the asset list
- `methodology` must include a scope note explaining why the current build is Minnesota-only if `profile_id = mn_mvp`

---

## 12. Product View Manifest

Top-level frontend navigation contract for published dashboard tabs.

| Field | Type | Description |
|-------|------|-------------|
| `view_id` | string | Stable view identifier such as `mn_high_detail_tab` |
| `label` | string | Frontend tab label |
| `detail_level` | enum | `high` or `low` |
| `dataset_profile_id` | string | Linked Dataset Profile identifier |
| `manifest_path` | string | Path to the linked Presentation Manifest |
| `default_metric` | string | Metric selected on initial load |
| `default_geography_level` | enum | `tract`, `county`, or `state` |
| `badge_text` | string | Optional UI badge, e.g. `High Detail` |
| `description` | string | Short explanation shown in the frontend |

**Validation rules**:
- `dataset_profile_id` must point to a published Dataset Profile
- `manifest_path` must resolve to a valid Presentation Manifest
- `detail_level = high` for `mn_high_detail`, `detail_level = low` for `usa_low_detail_county`

---

## 13. Dual-Path Payload Convention

Frontend-facing export convention for the two published views.

| Profile | Geography detail | Expected frontend payloads |
|---------|------------------|----------------------------|
| `mn_high_detail` | Minnesota tract-level + optional county/state summaries | tract tables, tract GeoJSON, optional county/state support tables |
| `usa_low_detail_county` | National county-level only | county tables, county GeoJSON, optional state support tables |

**Rule**: The pipeline may compute tract-level national data internally, but the `usa_low_detail_county` frontend contract publishes county-only detail assets.

---

## 14. County Origin Record

Canonical origin entity for the `usa_low_detail_county` routing path.

| Field | Type | Description |
|-------|------|-------------|
| `county_fips` | string | 5-digit county FIPS identifier |
| `state_fips` | string | 2-digit state FIPS identifier |
| `county_name` | string | County or county-equivalent name |
| `centroid_lat` | float | Latitude of routing origin centroid |
| `centroid_lon` | float | Longitude of routing origin centroid |
| `total_pop` | integer | County population denominator |
| `child_pop` | integer | County child population denominator |
| `geometry` | geometry | County geometry used for export and mapping |

**Validation rules**:
- `county_fips` must be unique per county record
- centroid coordinates must be non-null for every exported county
- `total_pop` must be present for every populated county used in BEI computation

---

## 15. County Travel-Time Matrix

Low-detail national routing matrix from county centroids to hospitals.

| Field | Type | Description |
|-------|------|-------------|
| `origin_id` | string | County FIPS identifier |
| `destination_id` | string | Hospital identifier such as `AHA_ID` |
| `duration_min` | float | Valhalla-derived drive time in minutes |
| `scenario` | enum | `ground_only` or another published routing scenario |
| `routing_engine` | string | Expected to be `valhalla` for this path |
| `status_code` | integer/null | Optional backend response code for diagnostics |
| `error_text` | string/null | Optional routing error text |

**Validation rules**:
- `origin_id` must map to a published county origin record
- `destination_id` must map to a facility record
- `duration_min` must be non-negative or `+inf` when no route exists
- low-detail national publication uses county origins only; no tract origins should appear in this matrix
