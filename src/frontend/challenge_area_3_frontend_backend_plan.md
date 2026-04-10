# Challenge Area 3 Product Plan
## Modern Front End + Python Backend Architecture for Burn Care Equity Visualization

## 1. Product goal
Build a modern, presentation-ready web application that answers **Challenge Area 3: Advancing Equitable Access to Burn Care**.

The app should answer one core question clearly:

**Where do structural inequities limit access to timely burn care?**

Based on the updated research, the product must now reflect that access is not a single static distance measure. It should represent **regionalized burn-system access** using:

- specialized burn-care supply
- direct access to definitive care
- transfer-aware access through stabilization-capable hospitals
- pediatric-specific access
- structural burn-bed capacity
- **transport scenario differences**, especially **ground-only baseline** versus **conditional ground-plus-air sensitivity**

This should feel like a polished health-tech decision-support platform, not a generic hospital map.

---

## 2. Strategic framing

### Primary use case
Your app should explicitly declare one primary use case:

**Equitable Access to Burn Care**

The product should not split its identity across referral networks and telemedicine. Those can appear only as secondary implications. The main story remains:

- structural burn-care access
- geographic inequity
- rural versus urban travel burden
- pediatric inequity
- structural capacity gaps
- how transport assumptions change what “access” means

### Product promise
A strong product promise would be:

> A national burn-care equity intelligence platform that visualizes structural access gaps using burn-center geography, pediatric capability, road and air transport scenarios, transfer-aware routing, and burn-bed capacity.

### What the product is
- A geographic access and equity analytics platform
- A visual explanation tool for structural disparities
- A presentation tool for judges and stakeholders
- A planning tool for policy and resource allocation discussions
- A scenario interface for comparing transport assumptions

### What the product is not
- Not a patient-level outcome predictor
- Not a real-time dispatch or flight operations tool
- Not a real-time open-bed monitor
- Not a clinical triage engine
- Not a guarantee of helicopter availability

That distinction must stay visible in the UI, especially when air transport appears.

---

## 3. Core product principles

### Principle 1: Story first, dashboard second
The opening experience should guide the viewer through a clear story:

1. Burn care access is uneven
2. Geography and system design shape access
3. Pediatric access is different from adult access
4. Rural areas may depend on tiered transfer pathways
5. Transport mode assumptions materially change access in some regions
6. Structural capacity remains limited in some regions
7. These gaps create actionable priorities

### Principle 2: Every major screen must map to a Challenge Area 3 deliverable
The app should visibly support:

- burn center distribution per capita
- rural versus urban travel burden
- pediatric access relative to child population
- burn-bed capacity in high-need or structurally weak regions
- **ground-only versus conditional ground-plus-air sensitivity**

### Principle 3: Composite score plus transparent components
If you show BEI, never show only the composite. The user must always be able to see:

- specialized supply scarcity
- timely access burden
- pediatric access gap
- structural capacity gap

The transport assumptions feeding timely access must also be visible.

### Principle 4: Maps should explain, not overwhelm
Maps are still the hero, but they must be paired with plain-English interpretation.

### Principle 5: Scenario honesty builds trust
Air transport should be presented as a **scenario-based sensitivity layer**, not as guaranteed operational truth.

Every air-related screen should clearly indicate:
- this is an accessibility scenario
- dispatch and handoff are modeled assumptions
- public infrastructure data supports feasibility, not live availability

### Principle 6: Designed for judges in a live demo
The app should support:
- fast load times
- obvious filters
- readable legends
- clear takeaway cards
- minimal clicks to reach a strong insight
- one-click switching between transport scenarios

---

## 4. Recommended tech stack

## Front end
### Framework
- **Next.js** with React
- Use the **App Router** structure

### Why Next.js fits
- Excellent for modern UI and polished demos
- Works well for a mix of narrative pages and interactive analysis views
- Supports fast initial load and route-based organization
- Good for a presentation-first product

### Front-end library categories
- **UI system** for cards, tabs, drawers, toggles, selectors, dialogs, chips, and sheets
- **Charting** for ranked bars, distributions, comparisons, scenario deltas, and component breakdowns
- **Maps** for choropleths, point layers, flow overlays, and travel-time surfaces
- **Motion** for subtle transitions and screen changes
- **Client state** for selected geography, selected metric, selected scenario, and compare mode

## Backend
### Framework
- **Python backend**, ideally **FastAPI**

### Why FastAPI fits
- Clean API-first structure
- Strong performance for data-serving
- Natural fit with pandas, geopandas, numpy, scikit-learn, and geospatial workflows
- Easy to expose precomputed metric tables and scenario outputs

### Backend responsibilities
The Python layer should handle:
- data ingestion and cleaning
- tract / county / state aggregation
- BEI component computation
- transport scenario modeling
- transfer-aware routing logic
- hotspot detection and rankings
- caching and precomputation
- exporting map-ready JSON or vector-friendly outputs

## Data and storage layer
### Core data
- **Challenge-provided NIRD**

### Augmentation layers
- ACS total population
- ACS child population
- TIGER/Line tract and county geometry
- RUCA rurality classification
- optional SVI overlay
- OpenStreetMap road network and OSRM outputs
- **FAA airport / heliport infrastructure** for air-access sensitivity scenarios

### Storage approach
- relational store for hospital and geography tables
- geospatial store or files for tract / county / state geometry
- object storage for precomputed scenario outputs
- cached API responses for national default views

---

## 5. Product architecture

## High-level architecture
### Front end responsibilities
- render maps and charts
- manage filters and drilldowns
- expose transport scenario controls
- show narrative interpretation
- coordinate compare mode and scenario mode
- display route or pathway explanations for selected case studies

### Backend responsibilities
- compute BEI and companion metrics
- compute direct travel time
- compute transfer-aware system time
- compute stabilization burden
- compute pediatric access measures
- compute burn-bed capacity measures
- generate ground-only and conditional ground-plus-air scenario outputs
- aggregate results by geography and rurality
- serve hotspot and ranking outputs

### Recommended API domains
Design the platform around stable domains:
- geography
- facilities
- metrics
- transport
- scenarios
- comparisons
- methodology
- recommendations

---

## 6. Information architecture
The app should have a small number of strong top-level pages.

## A. Landing page / Story overview
Purpose: explain the problem and immediately frame the product as a structural access platform.

### What it should contain
- headline with the Challenge Area 3 question
- concise explanation of structural inequity in burn care access
- KPI strip with 3 to 5 national facts
- hero map preview
- short block explaining that access depends on both **infrastructure and transport pathway assumptions**
- section preview cards for:
  - burn center distribution
  - rural travel burden
  - pediatric access
  - burn-bed capacity
  - transport scenarios
- button to enter the explorer

### Tone
Clean, executive-friendly, and public-health-tech.

## B. National Equity Explorer
Purpose: main interactive screen.

### Layout recommendation
A three-zone layout works best.

#### Left panel: controls
- geography level: tract, county, state
- metric selector
- adult / pediatric selector where relevant
- rural / urban filter
- verification / designation filter
- normalization toggle where appropriate
- **transport scenario toggle**:
  - ground-only baseline
  - conditional ground-plus-air sensitivity
- compare selector

#### Center panel: map
- choropleth or hybrid map
- optional point overlays for burn centers, trauma centers, pediatric-capable centers, and airports / heliports
- hover tooltips
- click-to-select geography

#### Right panel: insight drawer
- selected geography summary
- rank and percentile
- BEI component breakdown
- transport interpretation
- whether the selected geography changes materially between ground-only and air sensitivity
- peer comparison
- suggested interpretation in plain language

### Why this works
The user can see national context, explore a place, understand why it scores poorly, and see whether transport assumptions matter.

## C. Metric detail pages
Use focused views rather than stuffing everything into one page.

### 1. Burn Center Distribution
Should include:
- burn center coverage map
- burn centers per capita
- verified versus state-designated versus other capability breakdown
- state ranking chart
- narrative on sparse coverage

### 2. Rural vs Urban Travel Burden
Should include:
- map of timely access burden
- rural versus urban summary cards
- distribution plot by RUCA class
- transfer-aware interpretation panel
- scenario comparison showing where air sensitivity changes burden most

### 3. Pediatric Access View
Should include:
- pediatric access gap map
- child population context
- pediatric-capable facility overlay
- state ranking chart
- adult versus pediatric mismatch callout

### 4. Burn-Bed Capacity View
Should include:
- burn beds per 100,000 map
- capacity by state or region
- comparison of structurally weak versus stronger regions
- clear caveat that this is structural capacity, not live occupancy

### 5. Transport Scenario View
This is the major addition from the updated research.

Purpose: make the transport model visible and understandable.

Should include:
- map toggle between **ground-only** and **conditional ground-plus-air**
- difference map showing where accessibility improves under the air scenario
- selected-region route or pathway explanation
- summary cards for:
  - direct definitive route time
  - transfer-aware system time
  - stabilization access burden
- visual breakdown of the air path as:
  - dispatch
  - ground-to-launch
  - flight segment
  - landing-to-facility
  - handoff
- note that this is a modeled scenario using public infrastructure data and explicit assumptions

## D. Compare mode
Purpose: compare two regions quickly.

### Compare screen contents
- side-by-side summary cards
- mirrored BEI component bars
- travel burden comparison
- pediatric access comparison
- capacity comparison
- **transport scenario delta comparison**
- takeaway sentence in plain language

The best demo will compare one underserved geography with one better-served geography and show whether air sensitivity narrows the gap or not.

## E. Methodology and data transparency page
Purpose: increase trust and support judging criteria.

### Include
- what NIRD contains
- what NIRD does not contain
- BEI structure and its four pillars
- explanation of direct versus transfer-aware access
- explanation of ground-only and conditional ground-plus-air scenarios
- air transport decomposition and assumptions
- data sources
- processing workflow
- limitations and interpretation guidance

This page is especially important because the dataset is hospital-level, not patient-level.

## F. Recommendations / Action page
Purpose: translate analysis into real-world action.

### Include
- hotspot regions needing attention
- candidate policy actions
- pediatric resource priorities
- capacity investment targets
- rural routing or regional planning implications
- places where air sensitivity suggests meaningful accessibility improvement
- places where even air sensitivity does not solve the structural gap

---

## 7. Recommended user flows

## Flow 1: Judge demo flow
1. Open landing page
2. Show the national BEI map
3. Switch to rural versus urban travel burden
4. Toggle from ground-only to conditional ground-plus-air
5. Show how some regions improve and some remain structurally underserved
6. Switch to pediatric access
7. drill into one underserved geography
8. compare against a better-served geography
9. end on recommendations and feasibility

This tells a clear story and uses the air transport addition as a meaningful differentiator instead of a gimmick.

## Flow 2: Analyst exploration flow
1. Open National Equity Explorer
2. Select metric
3. change geography level
4. toggle transport scenario
5. click a region
6. inspect component breakdown
7. compare with peer regions
8. open the transport detail view if needed

## Flow 3: Policy stakeholder flow
1. Open recommendations page
2. review hotspots
3. identify whether the hotspot is supply-driven, pediatric-driven, capacity-driven, or transport-driven
4. examine whether the air scenario materially changes the result
5. review suggested actions

---

## 8. Recommended visual system

## Design direction
Aim for a modern health analytics aesthetic:
- soft light theme or muted dark theme
- clean whitespace
- restrained color palette
- high-contrast KPI cards
- subtle gradients and motion
- minimal clutter

## Color strategy
Use color semantically.

Suggested approach:
- neutral base for layout
- one accent color for interaction states
- one sequential palette for inequity or burden maps
- distinct but harmonized secondary accents for:
  - pediatric views
  - capacity views
  - transport views

The transport layer should not look like a flight-tracking app. Keep it clean and analytical.

## Typography
Use strong hierarchy:
- headline scale for major insights
- clean explanatory copy
- compact numeric cards
- readable legend labels and captions

## Motion
Use subtle transitions for:
- panel open and close
- scenario switching
- compare mode entry
- route pathway reveal
- component bar loading

Avoid flashy motion during live demos.

---

## 9. Chart and map strategy

## Map types to include
### Choropleth maps
Best for:
- BEI
- timely access burden
- pediatric access gap
- burn beds per 100,000
- transport scenario delta

### Point overlays
Best for:
- ABA-verified burn centers
- state-designated centers
- pediatric-capable facilities
- trauma stabilization sites
- airport / heliport infrastructure in transport view

### Flow or route overlays
Use sparingly.
Best for:
- selected case study only
- direct versus transfer-aware pathway explanation
- air-access path illustration in the transport view

### Ranked bar charts
Best for:
- state rankings
- county rankings within a state
- rural versus urban comparisons

### Distribution charts
Best for:
- travel time distribution by RUCA class
- pediatric access distribution
- capacity distribution
- scenario delta distribution

### Component breakdown bars
Best for:
- BEI component explanation
- comparing two regions

### Difference charts
Best for:
- showing the improvement or non-improvement from air sensitivity
- comparing direct route versus transfer-aware route

### Key rule
Every chart should answer a specific question and defend the main use case.

---

## 10. Data model and backend planning

## Core backend entities
### Facility
Fields may include:
- hospital identifier
- hospital name
- coordinates
- state, county, ZIP
- adult and pediatric burn capability
- adult and pediatric trauma capability
- ABA verification
- state designation
- total beds
- burn beds
- facility type classification

### Geography unit
- tract
- county
- state
- region

Associated attributes:
- total population
- child population
- rurality class
- optional vulnerability overlays
- geometry

### Metric snapshot
A precomputed table for each geography and scenario:
- BEI
- specialized supply scarcity
- timely access burden
- pediatric gap
- capacity gap
- nearest definitive time
- transfer-aware system time
- stabilization burden
- burn centers per capita
- beds per 100k
- rankings and percentiles

### Scenario table
Supports:
- ground-only baseline
- conditional ground-plus-air sensitivity
- adult versus pediatric view
- capacity factor sensitivity if needed
- different geography levels

### Transport infrastructure table
For the air-sensitivity layer:
- candidate airport / heliport locations
- facility linkage to launch / landing infrastructure
- scenario parameters for dispatch, handoff, and cruise speed
- feasibility flags

---

## 11. Recommended API design

## Core endpoint groups
### Geography endpoints
Return:
- supported geographies
- geometry metadata
- lookup info

### Metric endpoints
Return:
- map-ready values
- distributions
- ranking tables
- legends
- percentiles

### Facility endpoints
Return:
- burn center points
- trauma center points
- pediatric-capable points
- filtered overlays

### Transport endpoints
Return:
- scenario metadata
- direct route times
- transfer-aware route summaries
- air-sensitivity eligibility information
- selected-case route breakdowns

### Compare endpoints
Return:
- side-by-side summaries
- component deltas
- scenario deltas
- interpretation fragments if desired

### Methodology endpoints
Return:
- metric definitions
- scenario definitions
- data sources
- limitations
- last updated metadata

### API response philosophy
The frontend should receive presentation-friendly payloads. React should not assemble metric logic on the client.

---

## 12. Backend handoff: dual-path tabs (MN high-detail + USA low-detail county)

The pipeline publishes two frontend-ready tabs. Use the following layout for integration.

### Product views manifest (entry point)

- **Path**: `Data/output/manifests/product_views_manifest.json`
- **Purpose**: Top-level contract for the app; lists tabs (views) and points each to a profile-specific presentation manifest.
- **Views**:
  - `mn_high_detail_tab` → Minnesota tract-level (high detail); `manifest_path` → `manifests/mn_high_detail_manifest.json`
  - `usa_low_detail_county_tab` → USA county-level (low detail); `manifest_path` → `manifests/usa_low_detail_county_manifest.json`

### Per-tab presentation manifest

Each view’s `manifest_path` points to a **presentation manifest** that defines:

- **Profile**: `id`, `display_name`, `scope_level`, `output_prefix`, `origin_state_fips`, `destination_region`, `notes`
- **Scenarios**: `default` (e.g. `ground_only`), `enabled` (e.g. `["ground_only"]`)
- **Assets**: Geography-level → scenario → `table`, `geojson`, optional `access_table`, `rankings`
- **methodology**: `data_sources`, `limitations`, `scope_note`
- **ui_defaults**: `geography_level`, `metric`, `map_center`, `map_zoom`, optional `narrative_order`

### MN high-detail tab (tract)

- **Manifest**: `Data/output/manifests/mn_high_detail_manifest.json`
- **Tables**: `Data/output/tables/mn_high_detail_tract_bei.parquet`, `mn_high_detail_tract_access.parquet` (or legacy `mn_mvp_*`)
- **GeoJSON**: `Data/output/geojson/mn_high_detail_tract_bei_ground.geojson` (when exported)
- **Figures**: `Data/output/figures/mn_high_detail_tract_bei_map.png`
- **Default geography**: tract; default metric: BEI; map center/zoom for Minnesota.

### USA low-detail county tab (county)

- **Manifest**: `Data/output/manifests/usa_low_detail_county_manifest.json`
- **Tables**: `Data/output/tables/usa_low_detail_county_county_bei.parquet`, `usa_low_detail_county_county_access.parquet`
- **GeoJSON**: `Data/output/geojson/usa_low_detail_county_county_bei.geojson` (when exported)
- **Figures**: `Data/output/figures/usa_low_detail_county_county_bei_map.png`
- **Default geography**: county; default metric: BEI; map center/zoom for contiguous US.

### How to run the backend for both tabs

1. **MN path**: `python -m src.pipeline.mn_mvp_pipeline` (produces tract access/BEI and `mn_high_detail_manifest.json`).
2. **USA county path**: `python -m src.pipeline.usa_low_detail_county_valhalla` (build county matrix), then `python -m src.pipeline.usa_low_detail_county` (produces county access/BEI and `usa_low_detail_county_manifest.json`).
3. **Export**: `python -m src.pipeline.export` (writes profile GeoJSON and `product_views_manifest.json`).
4. **Visuals**: `python -m src.pipeline.visualize` (writes MN and USA figures).

Or run the full dual path in one go: `python -m src.pipeline.run_dual_path_pipeline`, then `python -m src.pipeline.export` and `python -m src.pipeline.visualize`.

---

## 13. Precomputation strategy
Because geospatial analytics can get heavy, precompute aggressively.

## Precompute these items
- BEI by tract, county, and state
- BEI components
- rural / urban summaries
- pediatric access summaries
- burn-bed capacity summaries
- ground-only transport outputs
- conditional ground-plus-air outputs
- scenario delta tables
- ranking tables
- percentile bands
- map-friendly geometry joins

## Compute on demand only when necessary
- comparing arbitrary geographies
- opening detailed route logic for selected case studies
- uncommon scenario variants beyond the main two published scenarios

This keeps the demo fast.

---

## 14. Feature prioritization

## Phase 1: Must-have for hackathon demo
### Core screens
- landing page
- National Equity Explorer
- pediatric access page
- rural versus urban travel burden page
- capacity page
- transport scenario page
- methodology page
- recommendations page

### Core interactions
- metric switcher
- geography drilldown
- scenario toggle
- hover and click tooltips
- component breakdown panel
- compare two regions

### Core outputs
- burn centers per capita
- travel burden
- pediatric access
- burn-bed capacity
- BEI with transparent decomposition
- ground-only versus air sensitivity difference

## Phase 2: Strong differentiators
- hotspot typology view
- selected-case route illustration
- shareable state URL
- export cards for presentation screenshots
- plain-language insight generation

## Phase 3: Nice-to-have after hackathon
- collaboration features
- downloadable reports
- annotation layer
- monitoring or scheduled updates

---

## 15. Recommended screen details

## Landing page
### Sections
1. Hero statement
2. National snapshot cards
3. Why this matters
4. Four challenge outputs
5. Transport sensitivity preview
6. Explore CTA

### Best content blocks
- concise national access framing
- preview map
- one sentence explaining that access is modeled both as a ground baseline and an air sensitivity scenario

## Explorer page
### Top bar
- app title
- metric selector
- geography selector
- adult / pediatric toggle
- **transport scenario toggle**
- compare button
- methodology link

### Main content
- map
- summary cards
- selected geography insight panel
- ranking strip

### Bottom support section
- distribution chart
- peer comparison table
- interpretation notes

## Pediatric page
### Must show
- child population-aware denominator
- pediatric-capable facilities
- pediatric gap rankings
- adult versus pediatric mismatch

## Rural travel page
### Must show
- average travel burden
- rurality distribution
- selected example regions
- explanation that regionalized systems matter
- scenario difference between ground-only and air sensitivity

## Capacity page
### Must show
- burn beds normalized by population
- structural capacity caveat
- hotspots with weak capacity
- optional need overlay comparison

## Transport page
### Must show
- direct route versus transfer-aware route
- ground-only versus air sensitivity toggle
- air path stage breakdown
- feasibility explanation
- case study panel for one selected geography
- clear limitation statement

## Recommendations page
### Format
Use policy-ready cards such as:
- strengthen pediatric burn coverage in X
- prioritize routing mitigation in Y
- evaluate burn-bed scarcity in Z
- examine multimodal transport value in A
- identify places where air sensitivity still does not close the access gap

---

## 16. UX details that will make the app feel premium

## Small design choices that matter
- sticky insight panel while the map changes
- plain-language legends
- one-click reset filters
- breadcrumb trail for drilldowns
- compact metric explanation under each title
- responsive hover states
- smooth scenario switching
- highlighted selected geography
- useful empty states

## Trust-building elements
- data source chips
- last updated label
- methodology link next to each metric
- tooltip definitions for ABA-verified, transfer-aware access, structural capacity, and air sensitivity
- explicit limitations note in transport views

---

## 17. Suggested metric framing for UI labels
Use product-friendly labels.

### Good UI labels
- Burn Care Equity Score
- Travel Burden to Definitive Burn Care
- Transfer-Aware System Access
- Pediatric Access Gap
- Burn Beds per 100,000 Residents
- Verified Burn Center Coverage
- Rural Access Disparity
- Air Transport Sensitivity

Keep technical names in secondary text only.

---

## 18. Recommended narrative for the live demo

### Opening
“We focused on one primary use case: equitable access to burn care. Our platform identifies where structural inequities limit timely access using geography, pediatric capability, travel burden, transport scenarios, and burn-bed capacity.”

### Middle
“Here is the national map. We can switch from the composite score to the challenge-specific views: burn center distribution, rural travel burden, pediatric access, and structural capacity. We can also compare a ground-only baseline with a conditional ground-plus-air scenario to show where transport assumptions meaningfully change access.”

### Drilldown
“If we click this region, we can see whether the gap is driven by supply scarcity, pediatric limitations, long travel burden, or weak capacity. We can also see whether the air sensitivity scenario narrows that burden or whether the region remains structurally underserved.”

### Close
“The product ends with actionable priorities: where to improve pediatric capability, where transport burden is highest, where burn-bed support is weak, and where multimodal transport may help but is not sufficient by itself.”

---

## 19. Risks to avoid

## Product risks
- too many filters at once
- too much academic language on the first screen
- showing a black-box composite score without decomposition
- treating the air layer like guaranteed operations
- mixing all three challenge areas into one product
- showing too many facility markers at national zoom

## Technical risks
- slow national map rendering
- large geometry payloads
- computing scenario outputs on demand during demo
- inconsistent geographic keys across datasets
- confusing scenario legends

## Messaging risks
- implying patient-level outcomes from hospital-level data
- implying real-time open beds from static counts
- implying guaranteed rotor-wing dispatch from infrastructure presence
- using “equity” language without showing concrete structural mechanisms

---

## 20. Ideal final deliverable shape
The strongest final version is a polished decision-support story application with:
- a compelling landing page
- one powerful national explorer
- focused views for travel, pediatric access, capacity, and transport scenarios
- transparent methodology
- compare mode
- actionable recommendations

This creates both:
- a strong hackathon presentation tool
- a credible prototype of a real structural burn-care access platform

---

## 21. Final recommendation
Structure the product around this concept:

**A modern burn-care equity intelligence platform that combines national structural access mapping, pediatric and capacity analysis, transfer-aware travel modeling, and road-versus-air scenario sensitivity into one clear, judge-friendly story.**

The design should prioritize:
1. one clear primary use case
2. one central explorer
3. challenge-output-specific modules
4. transparent transport assumptions
5. real-world actionability
