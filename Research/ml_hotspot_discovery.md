Plan for **Hotspot Discovery beyond the raw BEI** .

Our current methodology defines BEI as a **tract-level structural access and capacity score** built from four components—specialized supply scarcity, timely access burden, pediatric access gap, and structural capacity gap—and it treats need/exposure as a **separate overlay**, not part of the core score. It also emphasizes that NIRD is a **hospital-level infrastructure dataset**, so the hotspot layer should stay focused on structural inequity, not patient-level outcome prediction.   

## Hotspot discovery goal

The hotspot module should answer a broader question than “where is BEI highest?”

It should answer:

1. **Where are inequity hotspots concentrated?**
2. **What kind of hotspot is each place?**
3. **Which hotspots should be prioritized first?**
4. **Which findings are stable across reasonable assumptions?**

That matches our product direction, which already calls for hotspot detection, component breakdown, peer comparison, and recommendation-oriented outputs rather than a single black-box score.  

## Proposed analytic plan

### 1. Build the hotspot base table

Start with a tract-level analytic table where each tract has:

* BEI
* the four BEI components: `S, T, P, C`
* companion metrics already defined in the methodology:

  * nearest definitive burn time
  * centers per 100k
  * beds per 100k
  * pediatric access
* rurality class
* total population
* child population
* optional secondary overlays like SVI or validated injury proxy

This works because our current framework already recommends tract-level analysis, multi-level aggregation, and publishing companion metrics beside the composite BEI.  

### 2. Detect spatial hotspots on BEI itself

Use classical spatial hotspot methods first, before clustering.

Recommended methods:

* **Getis-Ord Gi*** for statistically significant high-BEI and low-BEI clusters
* **Local Moran’s I** to identify:

  * high-high clusters
  * low-low clusters
  * spatial outliers like high-low tracts

Why this matters:

* It shows whether bad BEI values are isolated or regionally concentrated
* Our research yields a judge-friendly “significant hotspot” map rather than just a ranked list

Primary output:

* national tract hotspot map
* county-aggregated hotspot map for presentation
* top hotspot corridors/regions by state

### 3. Discover hotspot types, not just hotspot intensity

This is the most important “beyond raw BEI” step.

Run clustering on standardized tract profiles such as:

`[S, T, P, C, NearestBurnTime, CentersPer100k, BedsPer100k, PedsAccess, RUCA, NeedOverlay]`

Recommended methods:

* **Hierarchical clustering** for interpretability
* **K-means** for a simple first pass
* **HDBSCAN** when our research requires irregular, non-spherical hotspot groups
* **PCA or UMAP** for visualization only

Our research enables labeling hotspot archetypes like:

* **Rural transfer-burden hotspots**
* **Pediatric access deserts**
* **Capacity-poor regions despite moderate geography**
* **Low-supply / low-capacity structural deserts**
* **High-need moderate-access zones**
* **Adult-served but pediatric-poor regions**

This fits our methodology especially well because the BEI is already decomposed into interpretable structural pillars and is meant to preserve regionalized care logic rather than misclassify rural systems purely by nearest-center distance.  

### 4. Add a separate priority layer

Do **not** redefine BEI. Keep it clean.

Instead, create a second-stage planning score for intervention priority:

`Priority = f(BEI, NeedOverlay, Rurality, PediatricMismatch, CapacityWeakness)`

A simple first version is:

`Priority_i = BEI_i × (1 + λ × NeedOverlay_i)`

Then optionally add a pediatric bonus or rural bonus for policy emphasis.

This is fully consistent with our current methodology, which explicitly says need should stay outside the core BEI and be used as a separate overlay for planning. 

### 5. Run component-specific hotspot analysis

Don’t only hotspot the final BEI.

Also run hotspot detection separately on:

* `T` timely access burden
* `P` pediatric access gap
* `C` structural capacity gap
* `CentersPer100k`
* `BedsPer100k`

Our research yields much stronger findings, because we can say:

* “This region is a hotspot because of pediatric scarcity”
* “This one is not a pure distance problem; it is a capacity problem”
* “This one has moderate access but poor structural bed support”

That also aligns with the frontend plan, which emphasizes transparent decomposition, metric detail views, and focused recommendations.  

### 6. Test hotspot stability

Because our BEI includes policy choices like transfer penalty, effective bed factor, and catchment bands, hotspot findings should be stress-tested.

Sensitivity tests:

* transfer penalty `τ = 30, 45, 60`
* effective capacity factor `u = 1.0, 0.75`
* routing assumption:

  * direct-only
  * transfer-aware
* catchment bands:

  * 30/60/90 baseline
  * tighter or looser variants

Then compute a **stability score**:

* percent of scenarios where a tract/county remains a hotspot
* percent of scenarios where its hotspot type stays the same

Best interpretation:

* **persistent hotspots** = strongest policy targets
* **conditional hotspots** = watch-list areas sensitive to assumptions

That is especially important because our methodology already treats transfer-aware access and effective structural capacity as scenario-sensitive choices. 

## Data sources

### Core source

**NIRD** should remain the base hospital layer. Use:

* geographic fields
* `ABA_VERIFIED`
* `BC_STATE_DESIGNATED`
* `BURN_ADULT`
* `BURN_PEDS`
* adult/pediatric trauma designation fields
* `TOTAL_BEDS`
* `BURN_BEDS` 

### Population and geography layers

Use:

* **ACS 5-year** for total population and child population
* **TIGER/Line** for tract geometry
* **Census Geocoder** for hospital geocoding / tract assignment
* **RUCA** for rural-urban stratification
* **OSRM** for road-network travel times 

### Optional contextual overlays

Use only as secondary layers:

* **SVI** for interpretation, not core BEI
* **public injury proxy** if our research can validate it
* optional disaster / EMS datasets for future extension  

## Expected outcomes

### Research outcomes

Our research yields:

* a national **BEI hotspot map**
* a **hotspot typology map**
* a ranked list of **top priority hotspots**
* rural vs urban hotspot comparisons
* pediatric-specific hotspot findings
* capacity-specific hotspot findings
* a scenario-stability summary

### Product outcomes

These can directly feed the app:

* “Hotspot regions needing attention”
* peer comparison views
* component breakdown panels
* recommendation cards by hotspot type
* plain-language explanations for judges and stakeholders  

### Policy / planning outcomes

This is where the work becomes actionable:

* identify where pediatric capability expansion would matter most
* identify counties/states with the worst travel burden
* identify structurally weak burn-bed regions
* identify where transfer-aware systems help versus where they fail
* identify candidate areas for future tele-burn or regionalization investments 

## Recommended implementation sequence

Phase 1:

* compute tract-level BEI table
* run Gi* and Local Moran’s I on BEI
* produce county rollups and ranked hotspot lists

Phase 2:

* cluster hotspot profiles into archetypes
* build need overlay and priority ranking
* generate hotspot labels and summaries

Phase 3:

* run sensitivity analysis
* compute hotspot persistence
* convert findings into recommendation cards and UI narratives
