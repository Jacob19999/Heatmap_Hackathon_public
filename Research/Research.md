# Revised Research Methodology

### Research Aim

This study develops a **Burn Equity Index (BEI)** that measures **structural inequities in timely burn-care access**. The BEI is designed as an **access and capacity model**, not a patient-outcome model and not a generic social vulnerability score. Its purpose is to evaluate where people face structural disadvantages in reaching specialized burn care under the constraints of available hospital infrastructure, travel burden, pediatric capability, and burn-bed capacity.

### Conceptual Framing

The revised methodology is grounded in the idea that **burn-care inequity is primarily a systems-access problem**. Because the NIRD dataset is a **hospital-level dataset** focused on burn-center designation, geography, and bed resources, the index should reflect **specialized supply, transfer-aware access, pediatric access, and structural capacity**. Demand-side or exposure variables are treated separately as optional overlays rather than core components, since local burn-incidence estimates are not reliably available at fine geographic scales from public data alone.

### Geographic Unit of Analysis

The recommended analytic unit is the **census tract**. This provides the best balance between spatial detail and feasibility because public datasets such as ACS, RUCA, and SVI are available at tract level, while census blocks are too fine and county-level analysis is too coarse to capture sub-county disparities. County, state, and regional results can then be produced by aggregating tract-level BEI scores.

### Data Sources

The model uses **challenge-provided NIRD + public/free augmentation layers** for geographic augmentation, routing, and contextual analysis:

- **NIRD** for burn-center status, trauma capability, pediatric services, and burn-bed counts
- **American Community Survey (ACS)** for tract-level total population and child population
- **TIGER/Line shapefiles** for census tract boundaries and centroids
- **Census Geocoder** for assigning hospital locations to census geography
- **USDA RUCA codes** for tract-level rural/urban classification
- **CDC Social Vulnerability Index (SVI)** as an optional contextual overlay
- **OpenStreetMap road network** plus **OSRM** for road-network travel times
- **FAA airport / heliport data** (for example, Airport Data & Information Portal / public airport-heliport records) for optional air-access sensitivity scenarios

This wording is intentionally precise: the public/free augmentation layers are verifiable, while **NIRD should be described as challenge-provided unless you later confirm an independent public bulk release source**.

### BEI Structure

The BEI is computed as a weighted composite of four structural dimensions:

$$
\mathrm{BEI}_i
=
100\left(
0.25S_i + 0.30T_i + 0.20P_i + 0.25C_i
\right)
$$

where:

- $S_i$ = **specialized supply scarcity**
- $T_i$ = **timely access burden**
- $P_i$ = **pediatric access gap**
- $C_i$ = **structural capacity gap**

A **higher BEI** indicates **worse structural inequity in timely burn-care access**.

### Component Definitions

#### 1. Specialized Supply Scarcity ($S_i$)

This component measures how limited access is to specialized burn-care facilities relative to the local population. Facilities are weighted by their capability, with the greatest weight given to **ABA-verified burn centers**, followed by **state-designated centers**, then **burn-capable non-verified hospitals**, and finally **trauma-only stabilization sites**. Accessibility is computed using a travel-time decay function so that nearer facilities contribute more than distant ones.

#### 2. Timely Access Burden ($T_i$)

This component captures the travel burden of reaching definitive burn care. It incorporates both:

- **Direct access** to the nearest definitive burn center
- **Transfer-aware access**, where a patient may first go to a local stabilization-capable hospital before transfer to a definitive burn center

This reflects the reality of regionalized burn systems, especially in rural areas. The timely access score therefore measures not only distance, but also the structural dependence on multi-step referral pathways.

#### 3. Pediatric Access Gap ($P_i$)

Because pediatric burn access is a specific challenge requirement and a distinct systems issue, pediatric access is modeled separately. This component uses child population denominators and pediatric-capable facility indicators from NIRD. It evaluates how well children in each tract can access pediatric burn-capable care.

#### 4. Structural Capacity Gap ($C_i$)

This component measures the adequacy of **structural burn-bed capacity** reachable from each tract. It uses NIRD-reported `BURN_BEDS` as a measure of infrastructure capacity. The methodology explicitly avoids interpreting this as real-time open-bed availability. A sensitivity analysis may optionally apply a conservative utilization factor to estimate "effective" structural capacity.

### Accessibility Modeling Approach

The revised methodology uses an **E2SFCA-style accessibility framework** combined with a **scenario-based transport model**. This is preferable to simple nearest-center distance because it accounts for:

- distance decay
- competition for resources
- access to multiple facilities
- differences in facility capability
- referral and transfer structure
- differences between **ground-only** and **multimodal ground-plus-air** access assumptions

Travel times should be modeled using a routing engine rather than Euclidean distance. The recommended transport formulation treats mode as part of the path definition rather than as a simple adjustment factor.

For any origin tract $i$ and facility $j$, let $m \in \{\text{road}, \text{air}\}$ denote transport mode. Then define a mode-specific travel time:

$$
t_{ij}^{(m)}
$$

where:

- $t_{ij}^{(\text{road})}$ = road-network time from OSRM or another free routing engine using OpenStreetMap road data
- $t_{ij}^{(\text{air})}$ = total air-access time, not just in-air flight time

The air pathway should be decomposed as:

$$
t_{ij}^{(\text{air})}
=
t_i^{\text{dispatch}}
+
t_i^{\text{ground-to-launch}}
+
t_{ij}^{\text{flight}}
+
t_j^{\text{landing-to-facility}}
+
t_{ij}^{\text{handoff}}
$$

This keeps the model structurally honest. Air access is represented as a multi-stage pathway requiring dispatch, launch access, the flight segment, and post-landing handoff. Because nationwide real-time air-ambulance dispatch availability is not readily available as a free public operational feed, the air term should be used as a **scenario-based sensitivity analysis**, not as a claim about guaranteed helicopter access.

To avoid overstating air access, define a feasibility rule:

$$
\tilde t_{ij}^{(m)} =
\begin{cases}
t_{ij}^{(m)}, & \text{if mode } m \text{ is allowed under the scenario} \\
+\infty, & \text{otherwise}
\end{cases}
$$

Then define direct access to definitive burn care as:

$$
T_i^{\text{dir}}
=
\min_{d \in \mathcal{D}}
\left[
\min_{m \in \{\text{road},\text{air}\}}
\tilde t_{id}^{(m)}
\right]
$$

and transfer-aware access as:

$$
T_i^{\text{trans}}
=
\min_{s \in \mathcal{S},\, d \in \mathcal{D}}
\left[
\min_{m_1 \in \{\text{road},\text{air}\}} \tilde t_{is}^{(m_1)}
+
\tau_s
+
\min_{m_2 \in \{\text{road},\text{air}\}} \tilde t_{sd}^{(m_2)}
\right]
$$

The overall system access time remains:

$$
T_i^{\text{sys}} = \min\left(T_i^{\text{dir}},\; T_i^{\text{trans}}\right)
$$

### Transport Scenarios and Public-Data Feasibility

The recommended reporting structure is to publish at least two scenarios:

1. **Ground-only baseline** using OpenStreetMap + OSRM road-network routing
2. **Conditional ground-plus-air sensitivity** using public FAA airport/heliport infrastructure data plus analyst-defined dispatch and handoff assumptions

A practical public-data implementation is:

- Use **OpenStreetMap / Geofabrik extracts** and **OSRM** for all surface legs
- Use **FAA airport / heliport records** to identify candidate launch and landing infrastructure for the air scenario
- Estimate the flight segment from coordinates using a transparent assumed cruise speed parameter
- Keep dispatch and handoff times as explicit scenario parameters rather than hidden constants

This means the project can support a reproducible air-access scenario with public/free infrastructure data, while still being honest that **real-time rotor-wing availability, weather restrictions, and operational dispatch rules are not directly observed in the public stack**.

### Treatment of Rurality and Social Context

**RUCA codes** are used to stratify and compare rural versus urban access burdens. This supports the challenge deliverable on rural/urban travel inequity. **SVI** and related social context variables should not be part of the core BEI, since the index is intended to measure structural burn-care access rather than general deprivation. Instead, SVI can be used as a **secondary lens** for interpretation or hotspot prioritization.

### Need and Exposure Overlay

The revised methodology does **not** include burn exposure or local injury burden as a core BEI pillar. This is intentional. Publicly available datasets do not reliably provide small-area burn incidence needed for defensible tract-level demand estimation. Instead, need should be presented as a separate overlay using variables such as:

- total population
- child population
- optional injury proxy, if validated

This keeps the BEI interpretable as a **pure structural access and capacity score**.

### Aggregation and Reporting

Although the BEI is computed at the tract level, results should be presented at multiple levels:

- **tract-level maps** for hotspots and fine-grained disparities
- **county-level summaries** using population-weighted averages of tract BEI scores
- **state or regional summaries** for policy comparison

In addition to the composite BEI, the methodology should report the challenge-specific outputs directly:

- burn centers per capita
- rural vs. urban travel burden
- pediatric access relative to child population
- structural burn-bed capacity in high- vs. low-need areas

### Methodological Contribution

The novelty of the revised methodology lies in reframing burn inequity as a **structural access and capacity problem** rather than a vulnerability-only or outcome-based model. Its main contributions are:

- use of a **tract-level structural equity index**
- integration of **transfer-aware access pathways**
- explicit separation of **pediatric access**
- distinction between **structural capacity** and real-time availability
- preservation of **regionalized, tiered care logic** so rural areas are not automatically misclassified as pure access deserts

### Final Methodological Position

In summary, the revised BEI methodology is a **tract-based, literature-informed structural access model**. The model uses **challenge-provided NIRD + public/free augmentation layers**, including ACS, TIGER/Line, Census Geocoder, RUCA, SVI, OpenStreetMap/OSRM, and optional FAA airport/heliport infrastructure for air-access sensitivity analysis. It is specifically tailored to Challenge Area 3 and is designed to quantify inequity in access to specialized burn care through four core dimensions: supply, timely access, pediatric access, and structural capacity.
