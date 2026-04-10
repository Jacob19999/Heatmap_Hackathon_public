# Phase 0 Research: BEI Analytics Pipeline

**Feature**: 001-phase1-bei-analytics
**Date**: 2026-03-14

This document records all technology decisions and resolved unknowns for the Phase 1 analytics pipeline.

---

## 1. OSRM Hosting Strategy

**Decision**: Self-host OSRM via Docker with a US-wide OpenStreetMap extract.

**Rationale**: The pipeline requires a travel-time matrix between ~84,000 census tract centroids and ~635 NIRD facilities. The OSRM public demo server (`router.project-osrm.org`) is rate-limited and not suitable for batch queries at this scale. Self-hosting allows unrestricted use of the `/table` endpoint for batch duration matrices.

**Alternatives considered**:
- *Public OSRM demo server*: Rejected — rate limits make national-scale computation impractical.
- *Google Maps / Mapbox APIs*: Rejected — cost-prohibitive for ~53M origin-destination pairs; introduces proprietary dependency.
- *Haversine / Euclidean distance*: Rejected — Constitution §4.4 requires road-network routing, not straight-line distance.
- *Valhalla routing engine*: Viable alternative; OSRM preferred for faster matrix computation and broader community adoption.

**Implementation**:
1. Download US-wide OSM extract from Geofabrik (`us-latest.osm.pbf`)
2. Run `osrm-extract`, `osrm-partition`, `osrm-customize` to prepare the data
3. Start `osrm-routed` in MLD mode via Docker
4. Query `/table/v1/driving` with batched coordinate lists

### 1a. Haversine prefilter for the travel-time matrix

**Decision**: Before calling OSRM, restrict tract–facility pairs using air-line (Haversine) distance: for each tract, keep only facilities within **300 km** Haversine, or the **closest 30 facilities** (whichever set is larger). Route only these candidate pairs via OSRM.

**Rationale** — no loss of accuracy:

1. **90-minute cutoff in the pipeline**  
   The step-decay function used in BEI (E2SFCA and access) is defined so that \(g(t) = 0\) for \(t > 90\) minutes driving (see `config.STEP_DECAY_BANDS_MIN` and `bei_components.step_decay`). Any facility reachable only in more than 90 minutes contributes **zero** to accessibility and will never be the “nearest” for access times. So we only need driving times for pairs that can plausibly be within 90 minutes.

2. **Why 300 km Haversine is safe**  
   - 90 minutes driving at US highway speeds (~100–110 km/h) ≈ **150–165 km** of **road** distance.  
   - Road distance is always ≥ Haversine; the detour factor (road / air-line) is typically **1.2–1.5×** (rural highways) and can reach **~2×** in mountainous or circuitous regions.  
   - So the Haversine distance at which 90 minutes driving is *still possible* is on the order of 165/2 ≈ **~80 km**.  
   - **300 km** Haversine implies at least ~360 km road (detour ≥ 1.2), i.e. **~3.3+ hours** at 110 km/h — well beyond the 90-minute cutoff.  
   - Therefore any tract–facility pair with Haversine > 300 km is guaranteed to have driving time > 90 minutes; excluding it from OSRM does not change any downstream result (E2SFCA or access times).

3. **Why keep at least 30 candidates per tract (min-K)**  
   For very remote tracts (e.g. rural Alaska, sparse Mountain West), fewer than 30 facilities may lie within 300 km. The pipeline still needs the true driving-nearest **definitive** and **stabilization** facilities for access (T_dir, T_stab, T_sys). Because Haversine distance is always ≤ driving distance, the driving-nearest facility is always among the Haversine-nearest. Keeping the **closest 30 by Haversine** ensures that the true nearest (and any other facility that could fall within 90 min driving) is in the candidate set. Thirty is conservative relative to the number of definitive (~135) and stabilization (~500+) facilities nationally and adds negligible extra OSRM cost for the small share of tracts with few facilities within 300 km.

**Effect**: The full Cartesian matrix has ~84,000 × 635 ≈ 53M pairs. The prefilter typically reduces this to ~1.5–2.5M pairs (~20–30× fewer), and OSRM requests from ~22,000 to ~2,000, cutting routing wall time by roughly an order of magnitude without changing any final BEI or access-time result.

**Config**: `config.ROUTING_MAX_HAVERSINE_KM` (default 300), `config.ROUTING_MIN_K` (default 30). Prefilter can be disabled with `compute_travel_time_matrix(..., prefilter=False)` for full Cartesian routing.

---

## 2. ACS Data Vintage and Tables

**Decision**: Use ACS 5-year 2022 estimates (2018–2022 vintage).

**Rationale**: This is the most recent completed 5-year ACS release available. Using 5-year estimates provides stable tract-level estimates for small geographies.

**Key tables**:
- `B01003` — Total population
- `B09001` — Population under 18 years (child population proxy)
- `B01001` — Sex by Age (finer child age breakdown if needed)

**Access method**: Census Bureau API (`api.census.gov`) with the `census` Python package or direct `requests` calls. Alternatively, download pre-tabulated tract-level files from `data.census.gov`.

**Alternatives considered**:
- *ACS 1-year*: Rejected — not available at tract level.
- *Decennial Census 2020*: Viable for total population but lacks socioeconomic variables; ACS is more current.

---

## 3. TIGER/Line Vintage and Format

**Decision**: Use TIGER/Line 2022 shapefiles matching the ACS 2022 vintage.

**Rationale**: Census tract boundaries must match the vintage of population data to avoid geographic misalignment. The 2022 TIGER/Line files use 2020 Census geography (which the 2022 ACS also uses).

**Format**: Shapefiles (`.shp`), loaded via `geopandas.read_file()`. Use tract-level files (`tl_2022_*_tract.shp`) by state, then concatenate nationally.

**Key fields**: `GEOID` (11-digit FIPS), `ALAND` (land area), `INTPTLAT`/`INTPTLON` (internal point for centroid).

---

## 4. RUCA Code Source and Join Strategy

**Decision**: Use USDA ERS RUCA codes (2010-based, updated with 2020 Census tract IDs where available).

**Rationale**: RUCA codes are the constitution-mandated rurality classification (§4.8). They are available at tract level and provide a 10-category urban-rural continuum.

**Join key**: Census tract FIPS code (GEOID). RUCA codes are distributed as Excel or CSV with tract FIPS.

**Rural/urban threshold**: Tracts with RUCA primary code ≥ 4 are classified as rural; 1–3 as urban. This follows standard USDA ERS guidance and aligns with common health services research practice.

**Alternatives considered**:
- *NCHS Urban-Rural Classification*: County-level only; too coarse for tract analysis.
- *RUCC codes*: County-level; same issue.

---

## 5. FAA Airport/Heliport Data

**Decision**: Use FAA Airport Data from the Airport Data & Information Portal (ADIP) or the raw APT_BASE.csv, filtering for heliports and airports with operational status.

**Rationale**: The air-access sensitivity scenario requires identifying plausible launch and landing points. FAA public data provides coordinates, facility type, and operational status for all U.S. airports and heliports.

**Key fields**: `location_id` (from ARPT_ID), `latitude` (LAT_DECIMAL), `longitude` (LONG_DECIMAL), `status` (O=operational), `facility_type` (AIRPORT/HELIPORT from SITE_TYPE_CODE A/H). Loader supports either pre-processed parquet or raw APT_BASE.csv with column mapping.

**Feasibility rule (implementation)**: The air scenario does **not** use Valhalla or OSRM. For each tract, the **closest** operational airport/heliport by **straight-line (Haversine) distance** is used as the launch site; for each facility, the **closest** airport by Haversine is used as the landing site. Ground-to-launch and landing-to-facility times are **estimated** as distance_km / `AIR_GROUND_SPEED_KMH` × 60 (minutes). Flight time is straight-line distance between launch and landing airports divided by cruise speed. See §5a below.

**Alternatives considered**:
- *Custom helipad databases*: Not consistently available as public bulk data.
- *Hospital helipad presence from NIRD*: Not included in the NIRD dataset.
- *Valhalla/OSRM for ground-to-launch and landing-to-facility*: Rejected for air scenario to avoid routing dependency and runtime; closest airport + straight-line is documented and sufficient for scenario sensitivity.

### 5a. Air scenario: no Valhalla — closest airport and straight-line distance

**Decision**: The ground-plus-air scenario does **not** call Valhalla or OSRM. All legs use closest airport by Haversine and straight-line time estimates.

**Rationale**:
- Keeps air scenario runnable without a routing backend and avoids large tract×airport and airport×facility routing matrices.
- Constitution §4.6 requires air to be modeled as scenario-based and assumption-dependent; straight-line and estimated ground speed are explicit, documented assumptions.
- Delivers the required transport-scenario comparison (ground-only vs ground-plus-air) without claiming road accuracy for the air ground legs.

**Implementation**:
- **Ground-to-launch**: For each tract centroid, find nearest FAA airport by Haversine; `duration_min = distance_km / (AIR_GROUND_SPEED_KMH / 60)`.
- **Landing-to-facility**: For each facility, find nearest FAA airport by Haversine; same formula.
- **Flight**: For each (tract, facility) pair use tract’s nearest launch airport and facility’s nearest landing airport; flight time = Haversine(launch, landing) / (AIR_CRUISE_SPEED_MPH × 1.60934 / 60) minutes.
- **End-to-end air time** = dispatch_min + ground_to_launch_min + flight_min + landing_to_facility_min + handoff_min.

**Config**: `AIR_GROUND_SPEED_KMH` (default 50), `AIR_CRUISE_SPEED_MPH` (default 150), `AIR_DISPATCH_MIN`, `AIR_HANDOFF_MIN`.

**Alternatives considered**:
- *Valhalla/OSRM for ground-to-launch and landing-to-facility*: Rejected — adds dependency and runtime for a sensitivity scenario; straight-line is acceptable and documented.

---

## 6. Spatial Statistics Library

**Decision**: PySAL ecosystem — specifically `esda` for spatial autocorrelation (Moran's I, Getis-Ord Gi*) and `libpysal` for spatial weights.

**Rationale**: PySAL is the standard Python library for spatial econometrics. `esda.Moran_Local` and `esda.G_Local` implement the exact statistics needed for hotspot detection.

**Spatial weights**: Queen contiguity weights (`libpysal.weights.Queen`) from tract geometry. This defines neighborhoods as tracts sharing a boundary or vertex.

**Alternatives considered**:
- *GeoDa (GUI)*: Not scriptable for pipeline integration.
- *R spdep*: Would require R interop; unnecessary when PySAL provides equivalent functionality.

---

## 7. Clustering Strategy

**Decision**: Two-pass approach — K-means for initial archetype discovery, HDBSCAN for density-based refinement.

**Rationale**: K-means provides a clean, interpretable first pass with controllable cluster count (target 4–8). HDBSCAN can then identify irregularly shaped clusters and noise points that K-means misses.

**Feature set for clustering**: Standardized (z-scored) tract profiles: `[S, T, P, C, NearestBurnTime, CentersPer100k, BedsPer100k, PedsAccess, RUCA_code]`.

**Cluster interpretation**: After clustering, compute mean component profiles per cluster to assign archetype labels (e.g., "rural transfer-burden hotspot," "pediatric access desert").

**Alternatives considered**:
- *Gaussian Mixture Models*: More flexible than K-means but harder to interpret for judges.
- *Spectral clustering*: Computationally expensive at 84k tracts; unnecessary for this feature set.

---

## 8. Geocoding Strategy

**Decision**: Two-stage geocoding — (1) use ZIP_CODE + STATE from NIRD to assign approximate coordinates, then (2) refine with Census Geocoder batch API using ADDRESS fields.

**Rationale**: NIRD provides `ADDRESS`, `ZIP_CODE`, `STATE`, and `COUNTY`. Many facilities can be matched by ZIP centroid alone (fast), with the Census Geocoder providing higher precision for address-level matching. The two-stage approach maximizes coverage.

**Tract assignment**: After geocoding to lat/lon, perform a spatial point-in-polygon join against TIGER/Line tract boundaries to assign each facility to a census tract GEOID.

**Fallback**: If geocoding fails for a facility, log it, attempt ZIP-centroid assignment, and document the impact on coverage metrics.

---

## 9. Output Format Strategy

**Decision**: Parquet for tabular outputs, GeoJSON for map-ready payloads.

**Rationale**: Parquet is columnar, compact, and fast to read — ideal for the large tract-level tables (~84k rows × ~30 columns). GeoJSON is the standard for web map rendering and is directly consumable by the Phase 2 frontend (Leaflet, Mapbox GL, Deck.gl).

**Output levels**:
- Tract-level: Full detail — BEI, S, T, P, C, companions, RUCA, scenario, hotspot labels
- County-level: Population-weighted aggregations
- State-level: Population-weighted aggregations + summary statistics
- Facility-level: Capability weights, designation, bed counts, coordinates

**Naming convention**: `{level}_{scenario}_{version}.parquet` (e.g., `tract_ground_v1.parquet`)

---

## 10. SVI Integration

**Decision**: Include CDC/ATSDR SVI as an optional secondary overlay, not a core pipeline dependency.

**Rationale**: Constitution §4.8 permits SVI only as a secondary interpretation lens. It is useful for contextual analysis (e.g., "this hotspot also has high social vulnerability") but MUST NOT influence the core BEI score.

**Implementation**: Download SVI tract-level data, join by GEOID, include in export tables as optional columns. Visualizations may show SVI as a separate overlay layer.

---

## 11. Testing Strategy

**Decision**: pytest for unit tests on critical computation modules + notebook-based visual sanity checks.

**Rationale**: The pipeline is exploratory and iterative — heavy unit testing of every function is less valuable than sanity checks on outputs. Critical functions (BEI formula, normalization, facility classification, system-time computation) warrant automated tests. Visual checks (do maps look right? do distributions make sense?) are best done in notebooks.

**Test priorities**:
1. BEI composite = weighted sum of components (algebraic check)
2. System time ≤ direct time for every tract (by construction)
3. Components bounded [0, 1] after normalization
4. Zero-burn-center states rank high in BEI
5. Facility classification logic matches weight tables

---

## 12. Configuration Management

**Decision**: Single `config.py` module with all paths, parameters, and scenario defaults as named constants.

**Rationale**: Centralizing configuration ensures that parameter changes for sensitivity analysis propagate consistently. No environment variables or config files needed for a local pipeline.

**Key configuration groups**:
- File paths (NIRD input, external data, output directories)
- BEI weights and sub-weights
- Step-decay band thresholds and weights
- Transfer penalty and stabilization threshold
- Air scenario parameters (dispatch, handoff, cruise speed, ground-to-launch max)
- Normalization percentiles
- Sensitivity sweep ranges

---

## 13. MVP Dataset Scope Strategy

**Decision**: Represent the Minnesota presentation build as a named dataset profile rather than as a permanently Minnesota-specific pipeline branch.

**Rationale**: The team needs a Minnesota-only MVP for the final presentation, but future work must be able to swap Minnesota in and out without rewriting compute logic, output naming, or frontend assumptions. A declarative profile keeps MN-specific paths, labels, and filtering rules in one place while shared BEI/access code remains reusable.

**Profile responsibilities**:
- Human-readable label for the active presentation scope
- Origin geography filter (Minnesota tracts for the current MVP)
- Destination geography filter (Minnesota plus border-state hospitals so cross-border access remains valid)
- Preferred matrix inputs and fallback paths
- Output file prefix / namespace for tables and GeoJSON
- Frontend display metadata such as default geography, scope name, and enabled scenarios

**Alternatives considered**:
- *Hardcode Minnesota directly in `mn_mvp_pipeline.py` only*: Rejected — easy short-term, but it creates a dead-end path for future state swaps and leaks presentation logic into reusable compute code.
- *Build everything national and let the frontend filter to Minnesota*: Rejected — wastes compute for the current presentation flow and makes payload downloads larger than needed.
- *Maintain separate per-state pipeline modules*: Rejected — duplicates logic and raises maintenance cost as additional scopes are introduced.

---

## 14. Frontend Scope Contract Strategy

**Decision**: Export a presentation manifest that tells the frontend which scope is active, which payloads belong to that scope, and which scenarios/metrics are available.

**Rationale**: The frontend should not guess file names like `mn_tract_bei.parquet` or infer whether a build is statewide, regional, or national. A manifest provides a stable handoff contract between Phase 1 precomputation and Phase 2 rendering. This matches the constitution's requirement that the backend return presentation-friendly payloads.

**Manifest contents**:
- Active profile ID and display name
- Geography coverage summary (`state`, `region`, or `national`)
- Data vintage and methodology notes
- Available scenarios and default scenario
- Table and GeoJSON asset locations by geography level
- Optional facility overlay asset locations
- Frontend hints such as default center/zoom, recommended narrative order, and available filters

**Alternatives considered**:
- *Have the frontend read directory listings directly*: Rejected — brittle, environment-specific, and not presentation-friendly.
- *Encode scope metadata only in filenames*: Rejected — filenames alone cannot express display labels, scenario availability, or narrative defaults cleanly.
- *Wait until FastAPI exists to define a contract*: Rejected — the frontend handoff already exists through precomputed files, so the contract should be defined now.

---

## 15. Dual-Path Product Detail Strategy

**Decision**: Publish two detail paths within the same product:

- `mn_high_detail` — Minnesota tract-level, matching the current MN MVP
- `usa_low_detail_county` — USA county-level aggregated view

**Rationale**: The judges need both a detailed, local, inspectable story and a whole-country view that loads quickly and stays legible. A Minnesota tract-level explorer is the right place for deep drilldown, while a USA county-level view preserves national context without requiring national tract geometries in the frontend.

**Alternatives considered**:
- *National tract-level frontend by default*: Rejected — payloads are larger, the UI is noisier, and the presentation story is less focused.
- *Minnesota-only product*: Rejected — loses national context and weakens the structural-access argument.
- *Two separate products/apps*: Rejected — violates the desired single-product experience and increases frontend/backend coordination cost.

---

## 16. National Low-Detail Export Strategy

**Decision**: The USA low-detail path should export county-level metric tables and county geometry only, even though the full pipeline still computes tract-level national outputs internally where needed.

**Rationale**: County-level aggregation is sufficient for the national tab and keeps the exported frontend assets small, fast, and judge-friendly. This also aligns with the constitution's precompute-first principle and the need for a fast demo.

**Implementation implications**:
- Continue computing the authoritative tract-level analytics where required for metric correctness
- Precompute county-level national outputs for frontend consumption
- Publish tract-level frontend assets only for the `mn_high_detail` profile
- Publish county-level frontend assets for the `usa_low_detail_county` profile

**Alternatives considered**:
- *Compute county-level metrics directly without tract-level base data*: Rejected — would complicate methodology consistency and reduce comparability with the tract-detail path.
- *Publish both tract and county geometry for the USA low-detail tab*: Rejected — unnecessary for the intended presentation level and increases payload size.

---

## 17. Frontend Tab/View Contract Strategy

**Decision**: Add a product-level views manifest that enumerates the frontend tabs and points each tab to its underlying dataset/profile manifest.

**Rationale**: The current single-profile manifest tells the frontend how to render one published dataset. A two-tab product needs a thin top-level contract that says, in effect, "render these two views: Minnesota High Detail and USA Low Detail County." This keeps the frontend logic declarative and avoids hardcoded tab wiring.

**Contract contents**:
- Product view ID and label
- Linked dataset/profile manifest path
- Default geography level and metric
- Hero narrative / ordering hints
- Optional badge text such as `High Detail` or `Low Detail`

**Alternatives considered**:
- *Hardcode the tabs in frontend code*: Rejected — fragile and duplicates backend publication logic.
- *Merge all assets into one giant manifest*: Rejected — makes the contract harder to reason about and mixes product navigation with dataset internals.

---

## 18. USA Low-Detail Routing Resolution Strategy

**Decision**: Build the `usa_low_detail_county` path from direct county-centroid to hospital Valhalla routing instead of computing a full national tract-to-hospital matrix and aggregating afterward.

**Rationale**: A full-country tract-level routing run is too expensive for the current hackathon compute and time budget. The low-detail USA tab does not need tract geometry or tract-by-tract frontend payloads, so routing directly from county centroids preserves genuine network travel-time estimation while reducing origin count dramatically. This keeps the national tab fast enough to build and practical enough to rerun during demo prep.

**Implementation implications**:
- Build a county analytic table with county FIPS, centroid latitude/longitude, and population denominators.
- Route county centroids to the same NIRD hospital destination set used by the national pipeline.
- Compute county-level direct/transfer-aware access and county-level BEI directly from the county matrix.
- Keep `mn_high_detail` on the existing Minnesota tract-level route matrix and cached outputs.
- Document that the USA low-detail tab is a county-resolution structural-access view, not a tract-resolution national estimate.

**Alternatives considered**:
- *Full national tract-to-hospital routing, then aggregate to county*: Rejected — too slow and expensive for the intended workflow.
- *Approximate county travel time by aggregating only Minnesota tract outputs during MVP*: Rejected as the long-term USA design — acceptable for temporary wiring tests only, but not a real national low-detail pipeline.
- *Use straight-line or centroid-distance heuristics without Valhalla*: Rejected — weaker methodology and less defensible for judge questions about driving access.

---

## 19. Metric Definitions, Assumptions, and Limitations

This section summarizes the main metrics, modeling assumptions, and known limitations for the Phase 1 BEI analytics pipeline. Implementation details live in `src/pipeline/` (e.g. `bei_components.py`, `config.py`, `routing.py`).

### Metric definitions

- **BEI (Burn Equity Index)**  
  Composite index: \( \text{BEI} = 100 \times (w_S S + w_T T + w_P P + w_C C) \), with default weights \( (w_S, w_T, w_P, w_C) = (0.25, 0.30, 0.20, 0.25) \). Each component is normalized to \([0, 1]\) (robust min–max or percentile-based) before weighting.

- **S (Supply)**  
  Supply-side access: E2SFCA-style step-decay over travel time to facilities; facilities weighted by capability (e.g. definitive vs stabilization). Step-decay bands and weights are configurable (e.g. 0–30, 30–60, 60–90 minutes; \( g(t) = 0 \) for \( t > 90 \) minutes).

- **T (Transfer / Time)**  
  Transfer-aware time component: combines system time (better of direct or transfer) with tier penalty. Longer system time and higher tier penalty reduce T. Uses the same step-decay cutoff (90 minutes) for consistency with access.

- **P (Pediatric)**  
  Pediatric-capable access: same E2SFCA structure as S but restricted to pediatric-capable facilities and (optionally) child population denominator.

- **C (Capacity)**  
  Capacity-weighted access: burn beds (or bed-equivalents) per capita within step-decay bands.

- **Access times**  
  Per-origin: direct time (nearest facility), transfer time (if applicable), system time = min(direct, transfer). Used as inputs to T and to step-decay in S, P, C.

- **Companion metrics**  
  Centers per 100k, beds per 100k, pediatric access ratio, etc., are derived from the same travel-time matrix and facility attributes; see export tables and `bei_composite.py`.

### Assumptions

- **90-minute cutoff**  
  Step-decay \( g(t) = 0 \) for \( t > 90 \) minutes driving. All routing and prefilter choices (e.g. 300 km Haversine, min-K candidates) are consistent with this: pairs that cannot be within 90 minutes are excluded or do not affect BEI/access.

- **Haversine prefilter**  
  For ground routing, only origin–destination pairs within 300 km Haversine (or the closest K destinations, whichever set is larger) are sent to Valhalla/OSRM. This does not change BEI or access results because farther pairs would exceed the 90-minute cutoff.

- **Ground routing only for structural access**  
  Valhalla or OSRM is used only for ground travel-time matrices (tract–facility or county–facility). Air scenario does not call Valhalla: ground-to-launch and landing-to-facility use closest airport by Haversine and estimated time from distance/speed.

- **Air scenario**  
  Straight-line (Haversine) distances and configurable speeds for ground-to-launch, flight, and landing-to-facility. Scenario-based; not a guarantee of transport availability.

- **RUCA rural/urban**  
  Tract-level RUCA primary code; rural = code ≥ 4, urban = 1–3. Used for challenge outputs and optional overlays.

- **Dual-path geography**  
  MN high-detail: tract-level origins (Minnesota tracts + cross-border facilities). USA low-detail: county-centroid origins; same NIRD facility set.

### Limitations

- **USA low-detail is county-resolution**  
  The national tab uses county-centroid to facility routing and county-level BEI/access. It is a structural-access view at county level, not a tract-level national estimate. MN high-detail remains tract-level.

- **Air scenario**  
  Air legs use closest airport and straight-line time estimates only. No road routing for ground-to-launch or landing-to-facility; sensitivity is to illustrate potential improvement, not to claim real-world air transport availability.

- **Routing fallbacks**  
  When Valhalla (or OSRM) fails for a pair, the pipeline records infinite duration and logs a fallback warning. Large numbers of inf pairs may indicate connectivity or coordinate issues; see routing performance guards and diagnostics CSVs.

- **Performance**  
  Full national tract-level routing is not in scope for the dual-path product; the USA path is intentionally county-based to keep build time and resource use manageable. Performance guards in `routing.py` warn when prefilter is disabled for large matrices or when batch count is very high.
