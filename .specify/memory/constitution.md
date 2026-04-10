

# Burn Care Equity Intelligence Platform — Constitution

## 1. Mission

This project exists to answer one primary question:

> **Where do structural inequities limit access to timely burn care?**

All specifications, plans, tasks, implementation choices, visualizations,
metrics, and claims MUST support **Challenge Area 3: Advancing Equitable
Access to Burn Care**.

The product MUST behave as a **burn-care equity intelligence platform** —
not as a generic hospital map, not as a referral-network optimization
product, and not as a telemedicine platform. Those may appear only as
secondary implications or future extensions.

This single-use-case focus is consistent with the judging guidance that
teams should identify one primary use case and be evaluated on depth and
rigor within that use case.

## 2. Non-Negotiable Scope Rules

### 2.1 Primary Use-Case Lock

The primary and only first-class use case is:

> **Equitable Access to Burn Care**

The project MUST NOT split its identity across Referral Networks,
Telemedicine, and Equity Access as co-equal products. Referral networks
and telemedicine may be mentioned only as:

- implementation implications
- future extensions
- supporting interpretation

They MUST NOT compete with the main product story, default UI, or
top-level success criteria. The main story stays on structural access,
rural/urban burden, pediatric inequity, structural capacity, and
transport assumptions.

### 2.2 Structural-Access Truthfulness

The system MUST be framed as a **structural access and capacity
analysis**. It MUST NOT claim to be:

- a patient-level outcome predictor
- a clinical triage engine
- a real-time dispatch tool
- a live air-operations system
- a real-time open-bed monitor
- a guaranteed helicopter-access estimator

BEI is an access-and-capacity model grounded in hospital infrastructure,
not patient outcomes. Air access is modeled only as a scenario-based
sensitivity layer, not operational truth.

### 2.3 Challenge-Output Alignment

Every major analytic module and every major frontend screen MUST map to
at least one of these outputs:

1. Burn center distribution per capita
2. Rural versus urban travel burden
3. Pediatric access relative to child population
4. Structural burn-bed capacity
5. Ground-only versus conditional ground-plus-air access sensitivity

Outputs 1–4 come from Challenge Area 3. Output 5 is a required product
extension because transport scenario comparison is a core explanatory
feature.

### 2.4 Composite Transparency

If a composite Burn Equity Index (BEI) is shown, it MUST NEVER appear
alone. The UI and API MUST always expose:

- the composite BEI
- each component score
- plain-language interpretation
- companion metrics
- the selected transport scenario

The BEI is explicitly decomposable into four pillars: specialized supply
scarcity, timely access burden, pediatric access gap, and structural
capacity gap.

## 3. Data Governance Principles

### 3.1 Base Dataset Truth

NIRD is the project's core hospital-resource layer. NIRD MUST be treated
as a challenge-provided hospital-level infrastructure dataset containing
facility location, designation, burn/trauma capability, pediatric
capability, and burn-bed counts.

NIRD MUST NOT be treated as:

- a patient registry
- a referral timestamp dataset
- a claims-based outcomes dataset
- a real-time capacity feed

### 3.2 Allowed Augmentation Sources

The system MAY augment NIRD with public/free sources for population
denominators, geography, rurality, routing, contextual overlays, and
air-access infrastructure sensitivity.

Approved augmentation categories:


| Category               | Purpose                               |
| ---------------------- | ------------------------------------- |
| ACS 5-Year             | Population / demographic denominators |
| TIGER/Line             | Census tract / county geometry        |
| Census Geocoder        | Facility geocoding                    |
| RUCA                   | Rural-urban classification            |
| SVI (optional)         | Social vulnerability context          |
| OpenStreetMap          | Road network for routing              |
| OSRM                   | Drive-time / distance computation     |
| FAA Airport / Heliport | Air-access infrastructure sensitivity |


### 3.3 Public-Availability Honesty

Documentation MUST distinguish between:

- challenge-provided NIRD
- public/free augmentation layers

The project MUST NOT claim that all inputs are public unless NIRD is
independently confirmed as public.

### 3.4 NIRD File Access Rules for AI Assistants

The NIRD dataset is stored in two files:

| File | AI Access |
|---|---|
| `Data/NIRD 20230130 Database_Hackathon_full_ai_ignore.xlsx` | **PROHIBITED** — AI MUST NOT read or inspect this file |
| `Data/NIRD 20230130 Database_Hackathon_sample.xlsx` | **ALLOWED** — AI MAY read this file for schema understanding, field inspection, and code development |

Rules:

- All production code MUST point to the full dataset file as its input
  path. The sample is for AI reference only.
- AI assistants MUST write code that loads from the full file, using the
  sample only to understand column names, types, and structure.
- AI assistants ARE allowed to see and analyze debugging outputs, error
  messages, logs, summary statistics, and printed results produced by
  running code against the full dataset.
- The restriction applies only to directly reading the raw full-dataset
  file, not to observing pipeline outputs derived from it.

### 3.5 No Fabricated Precision

Where data are missing, proxy-based, or scenario-derived:

- assumptions MUST be explicit
- scenario parameters MUST be documented
- feasibility logic MUST be visible
- limitations MUST appear in both methodology and UI

This is especially required for air-access modeling.

## 4. Metric Principles

### 4.1 Core BEI Framing

The canonical BEI MUST be defined as:

> **Higher BEI = worse structural inequity in timely burn-care access**

### 4.2 Required BEI Structure

The default BEI MUST include exactly these four structural components:


| Component                   | Symbol | Default Weight |
| --------------------------- | ------ | -------------- |
| Specialized supply scarcity | S      | 0.25           |
| Timely access burden        | T      | 0.30           |
| Pediatric access gap        | P      | 0.20           |
| Structural capacity gap     | C      | 0.25           |


Default weighted form:

```
BEI = 100 × (0.25·S + 0.30·T + 0.20·P + 0.25·C)
```

### 4.3 Need Remains Separate

Need, exposure, injury burden, or demand intensity MUST NOT be silently
folded into the core BEI. Those variables may appear only as:

- a separate overlay
- a planning priority layer
- optional contextual interpretation

Population and child population can support overlay logic, but small-area
burn incidence MUST NOT be embedded into the core BEI without defensible
data.

### 4.4 Timely Access Must Be Transfer-Aware

The T component MUST model burn access as a regionalized system, not just
nearest-facility distance. At minimum it MUST support:

- direct access to definitive burn care
- transfer-aware access through stabilization-capable hospitals
- a system-time formulation that allows the better of direct or
transfer-based pathways

### 4.5 Transport Scenario Policy

Transport MUST be modeled with at least two published scenarios:

1. **Ground-only baseline** — the default reporting baseline
2. **Conditional ground-plus-air sensitivity** — allowed only as a
  conditional accessibility sensitivity, never as a claim of guaranteed
   helicopter availability

### 4.6 Air-Access Honesty

If air is modeled, the system MUST represent it as a multi-stage path:

1. dispatch
2. ground-to-launch
3. flight
4. landing-to-facility
5. handoff

Air access MUST be described as scenario-based, infrastructure-supported,
and assumption-dependent. It MUST NOT be described as live dispatch
coverage, real-time medevac availability, or actual guaranteed transport
time.

### 4.7 Capacity Is Structural

`BURN_BEDS` and any derived capacity measure MUST be interpreted as
structural capacity, not live availability. Optional "effective capacity"
adjustments may be used only as explicit sensitivity scenarios.

### 4.8 Rurality and Social Context

- RUCA MUST be used for rural/urban stratification and comparison.
- SVI MAY be used only as a secondary interpretation lens, not as a core
BEI pillar.

## 5. Frontend Product Principles

### 5.1 Story First, Dashboard Second

The default user experience MUST tell a clear story before offering deep
exploration:

1. Burn care access is uneven
2. Geography and system design shape access
3. Pediatric access differs from adult access
4. Rural regions may depend on tiered transfer pathways
5. Transport assumptions change access in some places
6. Structural capacity is thin in some places
7. These patterns imply actionable priorities

### 5.2 Judge-Ready Demo Design

The live demo MUST optimize for:

- fast load
- few clicks
- readable legends
- obvious controls
- plain-language takeaways
- one-click scenario switching
- visually credible, modern presentation

### 5.3 Mandatory Top-Level Product Surfaces

The delivered product MUST include these surfaces (built in Phase 2
after the Phase 1 sanity-check gate passes):

1. Landing / Story Overview
2. National Equity Explorer
3. Burn Center Distribution view
4. Rural vs Urban Travel Burden view
5. Pediatric Access view
6. Burn-Bed Capacity view
7. Transport Scenario view
8. Methodology / Data Transparency page
9. Recommendations / Action page

### 5.4 Transport Scenario Visibility

The frontend MUST make transport assumptions visible. The product MUST
expose:

- current scenario selection
- ground-only vs conditional ground-plus-air comparison
- transport delta view where meaningful
- air-path stage explanation
- limitation note

### 5.5 Maps With Explanation

Maps are the hero, but every map MUST be paired with:

- an insight panel
- rank or percentile context
- component explanation
- transport interpretation where relevant
- a plain-language summary

### 5.6 Comparison Support

The product MUST support side-by-side comparison between geographies:

- BEI component comparison
- pediatric comparison
- capacity comparison
- transport scenario delta comparison

## 6. Backend and Architecture Principles

### 6.1 Frontend/Backend Separation

**Python backend** owns: ingestion, cleaning, geographic joins, metric
computation, transfer-aware routing logic, transport scenario outputs,
hotspot detection, precomputation, ranking tables, map-ready payloads.

**Frontend** owns: rendering, filtering, interaction, scenario toggles,
narrative explanation, compare mode, presentation flow.

### 6.2 Precompute First

National and common views MUST be precomputed where possible. At minimum
precompute:

- BEI by tract / county / state
- component scores
- rural/urban summaries
- pediatric summaries
- capacity summaries
- ground-only outputs
- conditional ground-plus-air outputs
- scenario deltas
- rankings
- percentile bands

### 6.3 Stable API Domains

APIs MUST be organized around durable domains:


| Domain          | Scope                                      |
| --------------- | ------------------------------------------ |
| geography       | Tracts, counties, states, geometries       |
| facilities      | NIRD hospitals, burn centers, capabilities |
| metrics         | BEI, components, companions                |
| transport       | Routing, scenarios, drive-times            |
| scenarios       | Ground-only, air, sensitivity parameters   |
| comparisons     | Side-by-side geography payloads            |
| methodology     | Definitions, sources, limitations          |
| recommendations | Actionable findings, priorities            |


### 6.4 Presentation-Ready Responses

The backend MUST return presentation-friendly payloads. The frontend MUST
NOT assemble raw metric logic from fragmented endpoints.

## 7. Validation and Quality Standards

### 7.1 Every Metric Needs a Definition

No metric may appear in the UI unless it has:

- a formal definition
- source inputs
- directionality
- scenario assumptions (if applicable)
- plain-language interpretation
- limitations

### 7.2 Sensitivity Analysis Requirement

The system MUST support sensitivity analysis for major policy choices:

- transfer penalty
- air-dispatch / handoff assumptions
- cruise-speed assumptions
- capacity utilization factor
- catchment bands
- routing scenario choice

### 7.3 Geographic Integrity

- All joins MUST use auditable geographic keys and documented logic.
- No silent many-to-many joins.
- No undocumented fallback geography rules.

### 7.4 Scope Honesty

The system MUST repeat the following limits consistently:

- not a patient-outcome model
- not real-time bed availability
- not guaranteed air transport access
- not operational dispatch truth

## 8. Required Delivery Sequence

Implementation is split into two hard phases with a mandatory gate
between them. Phase 2 MUST NOT begin until Phase 1 passes its sanity
check.

### Phase 1 — Data Processing, Analytics, Visualization & ML (Python)

All work in this phase uses Python and Python visualization libraries
(e.g. matplotlib, seaborn, plotly, folium, geopandas). The goal is to
produce validated, reproducible analytic outputs and exploratory
visualizations before any frontend or UI code is written.

1. Confirm Challenge Area 3 scope and success criteria
2. Finalize data dictionary, field mapping, and geographic joins
3. Build tract-level hospital-access analytic table
4. Compute challenge-specific direct outputs (distribution per capita,
   rural vs urban travel burden, pediatric access, bed capacity)
5. Build ground-only baseline routing
6. Add transfer-aware routing (direct + stabilize-and-transfer)
7. Add conditional ground-plus-air sensitivity scenario
8. Compute BEI components (S, T, P, C) and composite BEI
9. Validate companion metrics and scenario behavior
10. Run sensitivity analyses (transfer penalty, air assumptions,
    cruise speed, capacity factor, catchment bands)
11. Produce Python-based exploratory visualizations for every major
    output: choropleth maps, distribution plots, scatter comparisons,
    rural/urban stratifications, scenario deltas
12. Apply any ML techniques (clustering, hotspot detection, outlier
    identification, feature importance) where they strengthen the
    analytic story
13. Precompute national / state / county / tract output tables and
    map-ready GeoJSON payloads

### Phase 1 → Phase 2 Sanity-Check Gate

Phase 2 MUST NOT start until **all** of the following are confirmed:

- [ ] Every Section 2.3 output (1–5) has a validated, reproducible
      Python pipeline that produces correct results
- [ ] BEI components and composite pass directional sanity checks
      (higher BEI = worse equity; known-bad areas rank high)
- [ ] Ground-only and ground-plus-air scenarios produce plausible,
      distinguishable results with documented assumptions
- [ ] Transfer-aware T component returns better-of-direct-or-transfer
      times, not just nearest-facility distance
- [ ] Sensitivity analyses show the model responds meaningfully to
      parameter changes without pathological behavior
- [ ] All Python visualizations are reviewed for correctness, labeling,
      and interpretability
- [ ] Precomputed output tables and GeoJSON payloads are generated and
      spot-checked
- [ ] No metric violates Section 7.1 (definition, source, direction,
      interpretation, limitations documented)
- [ ] Data lineage from NIRD through augmentation to final metric is
      auditable and documented

Passing this gate means: the numbers are right, the methodology is
defensible, and the analytic story is solid before any UI investment.

### Phase 2 — UI and Frontend

Only after the sanity-check gate passes does frontend / UI work begin.
Phase 2 consumes the precomputed outputs from Phase 1 and focuses
entirely on presentation, interaction, and storytelling.

14. Build the frontend story flow (Section 5.1 narrative sequence)
15. Implement mandatory product surfaces (Section 5.3)
16. Add transport scenario toggles and delta views
17. Add compare mode and geographic side-by-side
18. Add methodology / data transparency page
19. Add recommendations / action page
20. Polish for judge-ready demo (Section 5.2 criteria)

The project MUST NOT start frontend work before the Phase 1 gate is
passed. Visual polish, interaction design, and presentation flow are
Phase 2 concerns only.

## 9. Definition of Done

### Feature-Level

A feature is only complete if it is:

- aligned to Challenge Area 3
- truthful to NIRD's limits
- explicit about scenario assumptions
- clear about structural vs real-time claims
- decomposable and interpretable
- fast enough for demo use
- supportive of judge storytelling
- useful for policy or planning discussion

### Release-Level

A release is only complete if it includes:

- one clear primary use case
- one coherent national explorer
- challenge-output-specific modules
- transport-scenario transparency
- methodology transparency
- actionable recommendations

## Governance

This constitution is the highest-authority document for the Burn Care
Equity Intelligence Platform. All specifications, plans, task lists,
implementations, and reviews MUST verify compliance with these principles.

**Amendment procedure:**

1. Proposed amendments MUST be documented with rationale.
2. Amendments MUST be reviewed against all dependent templates
  (plan-template, spec-template, tasks-template, checklist-template).
3. Version MUST be incremented per semantic versioning:
  - MAJOR: principle removal or incompatible redefinition
  - MINOR: new principle added or materially expanded guidance
  - PATCH: wording clarifications, typo fixes, non-semantic refinements
4. `LAST_AMENDED_DATE` MUST be updated on every change.

**Compliance review:**

- Every plan MUST include a Constitution Check gate (see plan-template).
- Every spec MUST map functional requirements to Section 2.3 outputs.
- Every task list MUST follow the delivery sequence in Section 8.
- No metric may ship without satisfying Section 7.1.

**Version**: 1.2.0 | **Ratified**: 2026-03-14 | **Last Amended**: 2026-03-14